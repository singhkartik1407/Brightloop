from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.plan import Plan
from app.models.quotation import Quotation, QuotationStatus
from app.models.subscription import (
    PendingBillingAdjustment,
    Subscription,
    SubscriptionCounter,
    SubscriptionEvent,
    SubscriptionLine,
    SubscriptionRenewalRecord,
    SubscriptionStatus,
)
from app.models.user import User
from app.modules.quotations.pricing import calculate_quotation
from app.modules.subscriptions.billing import (
    calculate_next_billing_date,
    calculate_normalized_monthly_value,
    round_money,
)
from app.modules.subscriptions.schemas import (
    PlanChangeResult,
    SubscriptionCreate,
    SubscriptionResponse,
)


def _generate_subscription_number(db: Session) -> str:
    current_year = datetime.now(timezone.utc).year
    prefix = f"SUB-{current_year}-"

    max_num_record = (
        db.query(Subscription.subscription_number)
        .filter(Subscription.subscription_number.like(f"{prefix}%"))
        .order_by(Subscription.subscription_number.desc())
        .first()
    )
    initial_seq = 1
    if max_num_record and max_num_record[0]:
        try:
            initial_seq = int(max_num_record[0].replace(prefix, "")) + 1
        except ValueError:
            initial_seq = 1

    insert_stmt = (
        pg_insert(SubscriptionCounter)
        .values(year=current_year, next_seq=initial_seq)
        .on_conflict_do_nothing(index_elements=["year"])
    )
    db.execute(insert_stmt)

    counter = (
        db.query(SubscriptionCounter)
        .filter(SubscriptionCounter.year == current_year)
        .with_for_update()
        .first()
    )

    seq = counter.next_seq
    counter.next_seq += 1
    db.flush()

    return f"{prefix}{seq:04d}"


def record_subscription_event(
    db: Session,
    subscription_id: uuid.UUID,
    event_type: str,
    description: str,
    actor: User | None = None,
    event_data: dict[str, Any] | None = None,
) -> SubscriptionEvent:
    event = SubscriptionEvent(
        subscription_id=subscription_id,
        event_type=event_type,
        actor_id=actor.id if actor else None,
        actor_role=actor.role if actor else "SYSTEM",
        description=description,
        event_data=event_data,
        created_at=datetime.now(timezone.utc),
    )
    db.add(event)
    return event


def convert_quotation_to_subscription(
    db: Session,
    quotation: Quotation,
    actor: User | None = None,
) -> Subscription:
    if quotation.status != QuotationStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "QUOTATION_NOT_ACCEPTED",
                "message": f"Cannot create subscription from quotation in '{quotation.status}' status. Only CONFIRMED quotations can be converted.",
            },
        )

    if quotation.subscription_id:
        existing_sub = db.get(Subscription, quotation.subscription_id)
        if existing_sub:
            return existing_sub

    plan = quotation.plan
    customer = quotation.customer

    start_date = quotation.start_date
    next_billing = calculate_next_billing_date(
        anchor_date=start_date,
        from_date=start_date,
        interval=plan.billing_interval,
        interval_count=plan.interval_count,
    )

    sub_number = _generate_subscription_number(db)

    # Recurring subtotal is the pre-tax total recurring commitment
    recurring_subtotal = Decimal(str(quotation.subtotal))

    subscription = Subscription(
        subscription_number=sub_number,
        customer_id=customer.id,
        plan_id=plan.id,
        quotation_id=quotation.id,
        status=SubscriptionStatus.CONFIRMED.value,
        start_date=start_date,
        expiry_date=next_billing,
        next_billing_date=next_billing,
        current_period_start=start_date,
        current_period_end=next_billing,
        billing_interval=plan.billing_interval,
        interval_count=plan.interval_count,
        recurring_subtotal=recurring_subtotal,
        currency=quotation.currency,
        cancel_at_period_end=False,
        billing_cycle_count=1,
        payment_terms=quotation.payment_terms,
        snapshot_data={
            "customerName": customer.display_name,
            "customerBillingState": customer.billing_state,
            "planName": plan.name,
            "planPrice": str(plan.price),
            "quotationNumber": quotation.quotation_number,
            "quotationTotal": str(quotation.total),
        },
    )

    for qline in quotation.lines:
        sline = SubscriptionLine(
            product_id=qline.product_id,
            description=qline.description,
            quantity=qline.quantity,
            unit_price=qline.unit_price,
            selected_variants=qline.selected_variants,
            taxes_data=qline.taxes_data,
            line_subtotal=qline.line_subtotal,
            tax_amount=qline.tax_amount,
            discount_amount=qline.discount_amount,
            line_total=qline.line_total,
        )
        subscription.lines.append(sline)

    db.add(subscription)
    db.flush()

    quotation.subscription_id = subscription.id

    record_subscription_event(
        db=db,
        subscription_id=subscription.id,
        event_type="CREATED",
        description=f"Subscription created from accepted quotation {quotation.quotation_number}",
        actor=actor,
        event_data={"quotationNumber": quotation.quotation_number},
    )

    return subscription


def create_direct_subscription(
    db: Session,
    payload: SubscriptionCreate,
    actor: User,
) -> Subscription:
    if payload.quotation_id:
        quotation = db.get(Quotation, payload.quotation_id)
        if not quotation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": "Quotation not found"},
            )
        if quotation.customer_id != payload.customer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": "Quotation customer mismatch"},
            )
        return convert_quotation_to_subscription(db, quotation, actor=actor)

    customer = db.get(Customer, payload.customer_id)
    if not customer or not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Customer not found or is inactive"},
        )

    plan = db.get(Plan, payload.plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Plan not found or is inactive"},
        )

    # Availability check
    if plan.available_from and payload.start_date < plan.available_from:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Plan is not yet available for start date"},
        )
    if plan.available_until and payload.start_date > plan.available_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Plan has expired and is not available for start date"},
        )

    total_qty = sum(l.quantity for l in payload.lines)
    if plan.min_quantity and total_qty < plan.min_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "BAD_REQUEST",
                "message": f"Total line quantity {total_qty} is below plan minimum quantity {plan.min_quantity}",
            },
        )

    # Calculate pricing
    calc = calculate_quotation(
        db=db,
        customer=customer,
        plan=plan,
        input_lines=payload.lines,
    )

    start_date = payload.start_date
    next_billing = calculate_next_billing_date(
        anchor_date=start_date,
        from_date=start_date,
        interval=plan.billing_interval,
        interval_count=plan.interval_count,
    )

    sub_number = _generate_subscription_number(db)

    subscription = Subscription(
        subscription_number=sub_number,
        customer_id=customer.id,
        plan_id=plan.id,
        quotation_id=None,
        status=SubscriptionStatus.CONFIRMED.value,
        start_date=start_date,
        expiry_date=next_billing,
        next_billing_date=next_billing,
        current_period_start=start_date,
        current_period_end=next_billing,
        billing_interval=plan.billing_interval,
        interval_count=plan.interval_count,
        recurring_subtotal=calc.subtotal,
        currency=plan.currency.upper(),
        cancel_at_period_end=False,
        billing_cycle_count=1,
        payment_terms=payload.payment_terms,
        snapshot_data={
            "customerName": customer.display_name,
            "customerBillingState": customer.billing_state,
            "planName": plan.name,
            "planPrice": str(plan.price),
        },
    )

    for cline in calc.lines:
        sline = SubscriptionLine(
            product_id=cline.product_id,
            description=cline.description,
            quantity=cline.quantity,
            unit_price=cline.unit_price,
            selected_variants=cline.selected_variants,
            taxes_data=cline.taxes_data,
            line_subtotal=cline.line_subtotal,
            tax_amount=cline.tax_amount,
            discount_amount=cline.discount_amount,
            line_total=cline.line_total,
        )
        subscription.lines.append(sline)

    db.add(subscription)
    db.flush()

    record_subscription_event(
        db=db,
        subscription_id=subscription.id,
        event_type="CREATED",
        description="Subscription created directly",
        actor=actor,
    )

    return subscription


def activate_subscription(
    db: Session,
    subscription: Subscription,
    actor: User,
) -> Subscription:
    if subscription.status == SubscriptionStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Subscription is already active"},
        )
    if subscription.status == SubscriptionStatus.CLOSED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Cannot activate closed subscription"},
        )

    subscription.status = SubscriptionStatus.ACTIVE.value
    record_subscription_event(
        db=db,
        subscription_id=subscription.id,
        event_type="ACTIVATED",
        description="Subscription activated",
        actor=actor,
    )
    return subscription


def pause_subscription(
    db: Session,
    subscription: Subscription,
    actor: User,
) -> Subscription:
    if not subscription.plan.allow_pause:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PLAN_PAUSE_NOT_ALLOWED", "message": "Plan policy does not permit pausing"},
        )
    if subscription.status != SubscriptionStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": f"Cannot pause subscription in '{subscription.status}' status"},
        )

    now_utc = datetime.now(timezone.utc)
    subscription.status = SubscriptionStatus.PAUSED.value
    subscription.paused_at = now_utc

    record_subscription_event(
        db=db,
        subscription_id=subscription.id,
        event_type="PAUSED",
        description="Subscription paused",
        actor=actor,
    )
    return subscription


def resume_subscription(
    db: Session,
    subscription: Subscription,
    actor: User,
) -> Subscription:
    if subscription.status != SubscriptionStatus.PAUSED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Subscription is not paused"},
        )

    now_utc = datetime.now(timezone.utc)
    if subscription.paused_at:
        pause_duration_days = (now_utc.date() - subscription.paused_at.date()).days
        if pause_duration_days > 0:
            from datetime import timedelta
            subscription.next_billing_date = subscription.next_billing_date + timedelta(days=pause_duration_days)
            subscription.current_period_end = subscription.current_period_end + timedelta(days=pause_duration_days)
            subscription.expiry_date = subscription.expiry_date + timedelta(days=pause_duration_days)

    subscription.status = SubscriptionStatus.ACTIVE.value
    subscription.resumed_at = now_utc
    subscription.paused_at = None

    record_subscription_event(
        db=db,
        subscription_id=subscription.id,
        event_type="RESUMED",
        description="Subscription resumed",
        actor=actor,
    )
    return subscription


def cancel_subscription(
    db: Session,
    subscription: Subscription,
    reason: str | None,
    actor: User,
) -> Subscription:
    if subscription.status in [SubscriptionStatus.CLOSED.value]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Subscription is already closed"},
        )

    now_utc = datetime.now(timezone.utc)
    subscription.cancel_at_period_end = True
    subscription.cancellation_requested_at = now_utc
    subscription.cancellation_reason = reason

    record_subscription_event(
        db=db,
        subscription_id=subscription.id,
        event_type="CANCELLATION_REQUESTED",
        description=f"Cancellation scheduled at period end ({subscription.expiry_date})",
        actor=actor,
        event_data={"reason": reason, "effectiveAt": str(subscription.expiry_date)},
    )
    return subscription


def close_subscription(
    db: Session,
    subscription: Subscription,
    actor: User,
) -> Subscription:
    if not subscription.plan.allow_early_close:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "EARLY_CLOSE_NOT_ALLOWED", "message": "Plan policy does not permit early close"},
        )
    if subscription.status == SubscriptionStatus.CLOSED.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": "Subscription is already closed"},
        )

    now_utc = datetime.now(timezone.utc)
    subscription.status = SubscriptionStatus.CLOSED.value
    subscription.closed_at = now_utc

    record_subscription_event(
        db=db,
        subscription_id=subscription.id,
        event_type="CLOSED",
        description="Subscription closed early",
        actor=actor,
    )
    return subscription


def renew_subscription(
    db: Session,
    subscription_id: uuid.UUID,
    actor: User | None = None,
    expected_renewal_date: date | None = None,
) -> Subscription:
    # Row-level lock on subscription for safe concurrency
    subscription = (
        db.query(Subscription)
        .filter(Subscription.id == subscription_id)
        .with_for_update()
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    if expected_renewal_date and subscription.next_billing_date > expected_renewal_date:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_RENEWAL_CYCLE",
                "message": f"Renewal for billing date {expected_renewal_date} has already been processed (current next billing date is {subscription.next_billing_date})",
            },
        )

    if subscription.status != SubscriptionStatus.ACTIVE.value:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "SUBSCRIPTION_NOT_RENEWABLE",
                "message": f"Cannot renew subscription in '{subscription.status}' status",
            },
        )

    if subscription.cancel_at_period_end:
        # Scheduled cancellation reached expiry
        subscription.status = SubscriptionStatus.CLOSED.value
        subscription.closed_at = datetime.now(timezone.utc)
        record_subscription_event(
            db=db,
            subscription_id=subscription.id,
            event_type="CLOSED",
            description="Subscription reached period end after scheduled cancellation and was closed",
            actor=actor,
        )
        db.commit()
        db.refresh(subscription)
        return subscription

    if subscription.plan.auto_close_at_end:
        # Plan policy dictates automatic closure at end of term
        subscription.status = SubscriptionStatus.CLOSED.value
        subscription.closed_at = datetime.now(timezone.utc)
        record_subscription_event(
            db=db,
            subscription_id=subscription.id,
            event_type="CLOSED",
            description="Subscription reached period end and was automatically closed per plan policy (autoCloseAtEnd)",
            actor=actor,
        )
        db.commit()
        db.refresh(subscription)
        return subscription

    if not subscription.plan.allow_renewal:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "PLAN_RENEWAL_NOT_ALLOWED", "message": "Plan policy does not permit renewal"},
        )

    # Next cycle calculation
    new_period_start = subscription.current_period_end
    new_period_end = calculate_next_billing_date(
        anchor_date=subscription.start_date,
        from_date=new_period_start,
        interval=subscription.billing_interval,
        interval_count=subscription.interval_count,
    )

    # Check for duplicate cycle processing (idempotency guard)
    existing_record = (
        db.query(SubscriptionRenewalRecord)
        .filter(
            SubscriptionRenewalRecord.subscription_id == subscription.id,
            SubscriptionRenewalRecord.period_start == new_period_start,
            SubscriptionRenewalRecord.period_end == new_period_end,
        )
        .first()
    )
    if existing_record:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_RENEWAL_CYCLE",
                "message": f"Renewal for cycle {new_period_start} to {new_period_end} has already been processed",
            },
        )

    # Apply deferred downgrade if queued
    downgrade_note = ""
    if subscription.pending_plan_id:
        pending_plan = db.get(Plan, subscription.pending_plan_id)
        if pending_plan and pending_plan.is_active:
            old_name = subscription.plan.name
            subscription.plan_id = pending_plan.id
            subscription.billing_interval = pending_plan.billing_interval
            subscription.interval_count = pending_plan.interval_count
            downgrade_note = f" (Applied deferred downgrade from {old_name} to {pending_plan.name})"
        subscription.pending_plan_id = None

    # Advance cycle
    subscription.current_period_start = new_period_start
    subscription.current_period_end = new_period_end
    subscription.next_billing_date = new_period_end
    subscription.expiry_date = new_period_end
    subscription.billing_cycle_count += 1

    renewal_record = SubscriptionRenewalRecord(
        subscription_id=subscription.id,
        cycle_number=subscription.billing_cycle_count,
        period_start=new_period_start,
        period_end=new_period_end,
        amount=subscription.recurring_subtotal,
        currency=subscription.currency,
        status="PROCESSED",
    )
    db.add(renewal_record)

    record_subscription_event(
        db=db,
        subscription_id=subscription.id,
        event_type="RENEWED",
        description=f"Subscription renewed for cycle {subscription.billing_cycle_count} ({new_period_start} to {new_period_end}){downgrade_note}",
        actor=actor,
        event_data={
            "cycle": subscription.billing_cycle_count,
            "periodStart": str(new_period_start),
            "periodEnd": str(new_period_end),
            "amount": str(subscription.recurring_subtotal),
        },
    )

    db.commit()
    db.refresh(subscription)
    return subscription


def change_subscription_plan(
    db: Session,
    subscription_id: uuid.UUID,
    new_plan_id: uuid.UUID,
    effective_at: datetime | None,
    actor: User,
) -> PlanChangeResult:
    subscription = (
        db.query(Subscription)
        .filter(Subscription.id == subscription_id)
        .with_for_update()
        .first()
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": "Subscription not found"},
        )

    if subscription.status not in [SubscriptionStatus.ACTIVE.value, SubscriptionStatus.CONFIRMED.value]:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "CONFLICT", "message": f"Cannot change plan in '{subscription.status}' status"},
        )

    new_plan = db.get(Plan, new_plan_id)
    if not new_plan or not new_plan.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Target plan not found or is inactive"},
        )

    if new_plan.currency.upper() != subscription.currency.upper():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "CURRENCY_MISMATCH",
                "message": f"Currency mismatch: Target plan currency '{new_plan.currency}' does not match subscription currency '{subscription.currency}'",
            },
        )

    current_plan = subscription.plan
    if current_plan.id == new_plan.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "BAD_REQUEST", "message": "Subscription is already on this plan"},
        )

    now_utc = datetime.now(timezone.utc)
    current_val = calculate_normalized_monthly_value(current_plan)
    new_val = calculate_normalized_monthly_value(new_plan)

    if new_val == current_val:
        # Same-value change: no charge, apply immediately
        subscription.plan_id = new_plan.id
        record_subscription_event(
            db=db,
            subscription_id=subscription.id,
            event_type="PLAN_CHANGED",
            description=f"Switched to equal-value plan '{new_plan.name}' with no additional charge",
            actor=actor,
            event_data={"oldPlanId": str(current_plan.id), "newPlanId": str(new_plan.id)},
        )
        db.commit()
        db.refresh(subscription)

        return PlanChangeResult(
            subscription=_serialize_subscription(subscription),
            adjustment_amount="0.00",
            currency=subscription.currency,
            effective_at=now_utc,
            adjustment_type="NO_CHARGE",
            invoice_id=None,
            message="Plan changed with no additional charge.",
        )

    elif new_val > current_val:
        # Upgrade: apply immediately, full difference charged (no time proration in MVP)
        if current_plan.billing_interval == new_plan.billing_interval and current_plan.interval_count == new_plan.interval_count:
            diff = round_money(Decimal(str(new_plan.price)) - Decimal(str(current_plan.price)))
        else:
            diff = round_money(max(Decimal("0.00"), Decimal(str(new_plan.price)) - Decimal(str(current_plan.price))))

        subscription.plan_id = new_plan.id
        subscription.billing_interval = new_plan.billing_interval
        subscription.interval_count = new_plan.interval_count

        adjustment = PendingBillingAdjustment(
            subscription_id=subscription.id,
            amount=diff,
            currency=subscription.currency,
            adjustment_type="IMMEDIATE_UPGRADE_DIFFERENCE",
            description=f"Immediate upgrade price difference from '{current_plan.name}' to '{new_plan.name}'",
            is_billed=False,
            created_at=now_utc,
        )
        db.add(adjustment)

        record_subscription_event(
            db=db,
            subscription_id=subscription.id,
            event_type="PLAN_UPGRADE",
            description=f"Upgraded to '{new_plan.name}'. Immediate difference of {subscription.currency} {diff:.2f} recorded",
            actor=actor,
            event_data={"oldPlan": current_plan.name, "newPlan": new_plan.name, "difference": str(diff)},
        )
        db.commit()
        db.refresh(subscription)

        return PlanChangeResult(
            subscription=_serialize_subscription(subscription),
            adjustment_amount=f"{diff:.2f}",
            currency=subscription.currency,
            effective_at=now_utc,
            adjustment_type="IMMEDIATE_UPGRADE_DIFFERENCE",
            invoice_id=None,
            message=f"Upgraded to {new_plan.name}. Additional charge of {subscription.currency} {diff:.2f} recorded for billing.",
        )

    else:
        # Downgrade: schedule for next renewal
        subscription.pending_plan_id = new_plan.id
        record_subscription_event(
            db=db,
            subscription_id=subscription.id,
            event_type="PLAN_DOWNGRADE_SCHEDULED",
            description=f"Downgrade to '{new_plan.name}' scheduled for next renewal ({subscription.next_billing_date})",
            actor=actor,
            event_data={"targetPlan": new_plan.name, "effectiveDate": str(subscription.next_billing_date)},
        )
        db.commit()
        db.refresh(subscription)

        from datetime import time
        eff_dt = datetime.combine(subscription.next_billing_date, time.min, tzinfo=timezone.utc)

        return PlanChangeResult(
            subscription=_serialize_subscription(subscription),
            adjustment_amount="0.00",
            currency=subscription.currency,
            effective_at=eff_dt,
            adjustment_type="DEFERRED_DOWNGRADE",
            invoice_id=None,
            message=f"Downgrade to {new_plan.name} scheduled for next renewal ({subscription.next_billing_date}).",
        )


def _serialize_subscription(subscription: Subscription) -> SubscriptionResponse:
    from app.modules.quotations.schemas import InvoiceLine, InvoiceTax

    lines = [
        InvoiceLine(
            product_id=line.product_id,
            description=line.description,
            quantity=line.quantity,
            unit_price=f"{line.unit_price:.2f}",
            selected_variants=line.selected_variants or [],
            taxes=[
                InvoiceTax(
                    name=t["name"],
                    code=t["code"],
                    rate_percent=str(t["ratePercent"]),
                    amount=str(t["amount"]),
                )
                for t in (line.taxes_data or [])
            ],
            line_subtotal=f"{line.line_subtotal:.2f}",
            tax_amount=f"{line.tax_amount:.2f}",
            discount_amount=f"{line.discount_amount:.2f}",
            line_total=f"{line.line_total:.2f}",
        )
        for line in subscription.lines
    ]

    customer_name = (
        subscription.customer.display_name
        if subscription.customer
        else (subscription.snapshot_data or {}).get("customerName", "")
    )
    plan_name = (
        subscription.plan.name
        if subscription.plan
        else (subscription.snapshot_data or {}).get("planName", "")
    )

    return SubscriptionResponse(
        id=subscription.id,
        number=subscription.subscription_number,
        customer_id=subscription.customer_id,
        customer_name=customer_name,
        plan_id=subscription.plan_id,
        plan_name=plan_name,
        quotation_id=subscription.quotation_id,
        pending_plan_id=subscription.pending_plan_id,
        status=SubscriptionStatus(subscription.status),
        start_date=subscription.start_date,
        expiry_date=subscription.expiry_date,
        next_billing_date=subscription.next_billing_date,
        billing_interval=subscription.billing_interval,
        payment_terms=subscription.payment_terms,
        lines=lines,
        recurring_subtotal=f"{subscription.recurring_subtotal:.2f}",
        currency=subscription.currency,
        cancel_at_period_end=subscription.cancel_at_period_end,
        cancellation_requested_at=subscription.cancellation_requested_at,
        paused_at=subscription.paused_at,
        created_at=subscription.created_at,
    )
