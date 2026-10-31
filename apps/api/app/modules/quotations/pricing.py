from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.customer import Customer
from app.models.discount import DiscountRule, DiscountScope, DiscountType
from app.models.plan import Plan
from app.models.product import Product, ProductVariant
from app.models.tax import TaxRule, TaxType
from app.modules.quotation_templates.schemas import SubscriptionLineInput


def round_money(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_active_window(rule: DiscountRule, now: datetime) -> bool:
    starts = ensure_utc(rule.starts_at)
    ends = ensure_utc(rule.ends_at)
    if not starts or not ends:
        return False
    return starts <= now <= ends


@dataclass
class CalculatedLine:
    product_id: uuid.UUID | None
    description: str
    quantity: int
    unit_price: Decimal
    selected_variants: list[str]
    taxes_data: list[dict[str, Any]]
    line_subtotal: Decimal
    tax_amount: Decimal = Decimal("0.00")
    discount_amount: Decimal = Decimal("0.00")
    line_total: Decimal = Decimal("0.00")
    has_inclusive_tax: bool = False
    tax_rules: list[TaxRule] = field(default_factory=list)


@dataclass
class CalculationResult:
    lines: list[CalculatedLine]
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    currency: str
    discount_rule_id: uuid.UUID | None
    winning_discount: DiscountRule | None
    snapshot_data: dict[str, Any]


def calculate_quotation(
    db: Session,
    customer: Customer,
    plan: Plan,
    input_lines: list[SubscriptionLineInput],
    discount_code: str | None = None,
    template_name: str | None = None,
) -> CalculationResult:
    # 1. Currency alignment
    currency = plan.currency.upper()

    calculated_lines: list[CalculatedLine] = []

    # 2. Plan line (representing recurring plan base fee)
    plan_price = Decimal(str(plan.price))
    plan_desc = f"Plan: {plan.name} ({plan.billing_interval})"
    plan_line = CalculatedLine(
        product_id=plan.product_id,
        description=plan_desc,
        quantity=1,
        unit_price=plan_price,
        selected_variants=[],
        taxes_data=[],
        line_subtotal=plan_price,
    )
    calculated_lines.append(plan_line)

    # 3. Product lines
    for item in input_lines:
        product = db.get(Product, item.product_id)
        if not product or not product.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": f"Product '{item.product_id}' not found or is inactive"},
            )

        if product.currency.upper() != currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "BAD_REQUEST",
                    "message": f"Product currency '{product.currency}' does not match plan currency '{currency}'",
                },
            )

        base_price = Decimal(str(product.sales_price))
        variant_delta_sum = Decimal("0.00")
        variant_names: list[str] = []

        if item.selected_variant_ids:
            seen_attrs = set()
            for v_id in item.selected_variant_ids:
                variant = db.get(ProductVariant, v_id)
                if not variant or variant.product_id != item.product_id or not variant.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "BAD_REQUEST",
                            "message": f"Variant '{v_id}' does not belong to product '{item.product_id}' or is inactive",
                        },
                    )
                attr_lower = variant.attribute_name.strip().lower()
                if attr_lower in seen_attrs:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "code": "BAD_REQUEST",
                            "message": f"Duplicate variant attribute '{variant.attribute_name}' on the same line",
                        },
                    )
                seen_attrs.add(attr_lower)
                variant_delta_sum += Decimal(str(variant.price_adjustment))
                variant_names.append(f"{variant.attribute_name}: {variant.attribute_value}")

        unit_price = round_money(base_price + variant_delta_sum)
        line_subtotal = round_money(unit_price * item.quantity)

        # Tax resolution for line
        line_tax_rules: list[TaxRule] = []
        if item.tax_rule_ids is not None:
            for t_id in item.tax_rule_ids:
                tax_r = db.get(TaxRule, t_id)
                if not tax_r or not tax_r.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={"code": "BAD_REQUEST", "message": f"Tax rule '{t_id}' not found or is inactive"},
                    )
                line_tax_rules.append(tax_r)
        else:
            # Automated GST place-of-supply determination requires configured seller state and customer billing state
            org_state = (settings.ORGANIZATION_STATE or "").strip()
            if not org_state:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "SELLER_STATE_NOT_CONFIGURED",
                        "message": "Seller organization registration state is not configured for automatic GST place-of-supply determination",
                    },
                )
            if not customer.billing_state or not customer.billing_state.strip():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "code": "CUSTOMER_BILLING_STATE_REQUIRED",
                        "message": "Customer billing state is required for automatic GST place-of-supply determination",
                    },
                )

            cust_state = customer.billing_state.strip()
            if cust_state.lower() == org_state.lower():
                # Intra-state: CGST + SGST
                cgst_sgst_rules = db.scalars(
                    select(TaxRule).where(
                        TaxRule.is_active == True,
                        TaxRule.tax_type.in_([TaxType.CGST.value, TaxType.SGST.value]),
                    )
                ).all()
                line_tax_rules.extend(cgst_sgst_rules)
            else:
                # Inter-state: IGST
                igst_rules = db.scalars(
                    select(TaxRule).where(
                        TaxRule.is_active == True,
                        TaxRule.tax_type == TaxType.IGST.value,
                    )
                ).all()
                line_tax_rules.extend(igst_rules)

        prod_line = CalculatedLine(
            product_id=item.product_id,
            description=product.name,
            quantity=item.quantity,
            unit_price=unit_price,
            selected_variants=variant_names,
            taxes_data=[],
            line_subtotal=line_subtotal,
            tax_rules=line_tax_rules,
        )
        calculated_lines.append(prod_line)

    subtotal = sum(l.line_subtotal for l in calculated_lines)

    # 4. Discount resolution (highest eligible saving, strictly no stacking)
    now_utc = datetime.now(timezone.utc)
    candidate_rules: list[DiscountRule] = []

    if discount_code:
        code_candidates = db.scalars(
            select(DiscountRule).where(
                DiscountRule.code.ilike(discount_code.strip()),
                DiscountRule.is_active == True,
            )
        ).all()
        matching_rule = next((c for c in code_candidates if _is_active_window(c, now_utc)), None)
        if not matching_rule:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": f"Discount code '{discount_code}' is invalid or expired"},
            )
        if matching_rule.max_uses is not None and matching_rule.used_count >= matching_rule.max_uses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "BAD_REQUEST", "message": f"Discount code '{discount_code}' has reached maximum uses"},
            )
        candidate_rules = [matching_rule]
    else:
        # Evaluate automatic active candidates
        candidates = db.scalars(
            select(DiscountRule).where(DiscountRule.is_active == True)
        ).all()
        candidate_rules = [
            c for c in candidates if _is_active_window(c, now_utc) and (c.max_uses is None or c.used_count < c.max_uses)
        ]

    # Evaluate savings for each candidate
    best_rule: DiscountRule | None = None
    best_saving = Decimal("0.00")
    best_matching_lines: list[CalculatedLine] = []

    for rule in candidate_rules:
        rule_val = Decimal(str(rule.value))
        if rule.scope == DiscountScope.PRODUCT.value:
            target_pids = {t.product_id for t in rule.targets}
            matching = [l for l in calculated_lines if l.product_id and l.product_id in target_pids]
            if not matching:
                continue

            matching_qty = sum(l.quantity for l in matching)
            matching_subtotal = sum(l.line_subtotal for l in matching)

            if rule.minimum_quantity is not None and matching_qty < rule.minimum_quantity:
                continue
            if rule.minimum_purchase is not None and matching_subtotal < Decimal(str(rule.minimum_purchase)):
                continue

            if rule.discount_type == DiscountType.PERCENTAGE.value:
                saving = round_money(matching_subtotal * rule_val / Decimal("100"))
            else:
                saving = min(rule_val, matching_subtotal)

            if saving > best_saving or (saving == best_saving and best_rule and best_rule.scope == DiscountScope.SUBSCRIPTION.value):
                best_saving = saving
                best_rule = rule
                best_matching_lines = matching

        elif rule.scope == DiscountScope.SUBSCRIPTION.value:
            total_qty = sum(l.quantity for l in calculated_lines)
            if rule.minimum_quantity is not None and total_qty < rule.minimum_quantity:
                continue
            if rule.minimum_purchase is not None and subtotal < Decimal(str(rule.minimum_purchase)):
                continue

            if rule.discount_type == DiscountType.PERCENTAGE.value:
                saving = round_money(subtotal * rule_val / Decimal("100"))
            else:
                saving = min(rule_val, subtotal)

            if saving > best_saving:
                best_saving = saving
                best_rule = rule
                best_matching_lines = calculated_lines

    # Apply single winning discount across lines
    discount_total = best_saving
    discount_rule_id = best_rule.id if best_rule else None

    if best_rule and best_saving > Decimal("0.00") and best_matching_lines:
        base_sum = sum(l.line_subtotal for l in best_matching_lines)
        if base_sum > Decimal("0.00"):
            allocated_so_far = Decimal("0.00")
            for idx, line in enumerate(best_matching_lines):
                if idx == len(best_matching_lines) - 1:
                    # Allocate remaining to avoid rounding discrepancy
                    line.discount_amount = best_saving - allocated_so_far
                else:
                    line_disc = round_money(best_saving * line.line_subtotal / base_sum)
                    line.discount_amount = line_disc
                    allocated_so_far += line_disc

    # 5. Tax calculation on net line amount
    tax_total = Decimal("0.00")
    for line in calculated_lines:
        line_taxable = max(Decimal("0.00"), line.line_subtotal - line.discount_amount)
        line_tax_sum = Decimal("0.00")

        inclusive_rules = [r for r in line.tax_rules if r.is_inclusive]
        exclusive_rules = [r for r in line.tax_rules if not r.is_inclusive]

        total_inclusive_rate = sum(Decimal(str(r.rate_percent)) for r in inclusive_rules)

        if total_inclusive_rate > Decimal("0.00"):
            total_inclusive_tax = round_money(
                line_taxable * total_inclusive_rate / (Decimal("100") + total_inclusive_rate)
            )
            base_taxable = line_taxable - total_inclusive_tax
            line.has_inclusive_tax = True

            allocated_inclusive = Decimal("0.00")
            for idx, tax_r in enumerate(inclusive_rules):
                r_rate = Decimal(str(tax_r.rate_percent))
                if idx == len(inclusive_rules) - 1:
                    t_amt = total_inclusive_tax - allocated_inclusive
                else:
                    t_amt = round_money(total_inclusive_tax * r_rate / total_inclusive_rate)
                    allocated_inclusive += t_amt

                line_tax_sum += t_amt
                line.taxes_data.append({
                    "name": tax_r.name,
                    "code": tax_r.code,
                    "ratePercent": str(tax_r.rate_percent),
                    "amount": f"{t_amt:.2f}",
                })
        else:
            total_inclusive_tax = Decimal("0.00")
            base_taxable = line_taxable
            line.has_inclusive_tax = False

        total_exclusive_tax = Decimal("0.00")
        for tax_r in exclusive_rules:
            r_rate = Decimal(str(tax_r.rate_percent))
            t_amt = round_money(base_taxable * r_rate / Decimal("100"))
            total_exclusive_tax += t_amt
            line_tax_sum += t_amt
            line.taxes_data.append({
                "name": tax_r.name,
                "code": tax_r.code,
                "ratePercent": str(tax_r.rate_percent),
                "amount": f"{t_amt:.2f}",
            })

        line.tax_amount = line_tax_sum
        tax_total += line_tax_sum
        line.line_total = line_taxable + total_exclusive_tax

    total = sum(l.line_total for l in calculated_lines)

    snapshot_data = {
        "customerName": customer.display_name,
        "customerCode": getattr(customer, "customer_code", None),
        "customerBillingState": customer.billing_state,
        "planName": plan.name,
        "planPrice": str(plan.price),
        "planBillingInterval": plan.billing_interval,
        "templateName": template_name,
        "appliedDiscountName": best_rule.name if best_rule else None,
        "appliedDiscountCode": best_rule.code if best_rule else None,
        "appliedDiscountSaving": str(discount_total),
    }

    return CalculationResult(
        lines=calculated_lines,
        subtotal=round_money(subtotal),
        discount_total=round_money(discount_total),
        tax_total=round_money(tax_total),
        total=round_money(total),
        currency=currency,
        discount_rule_id=discount_rule_id,
        winning_discount=best_rule,
        snapshot_data=snapshot_data,
    )
