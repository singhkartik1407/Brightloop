from __future__ import annotations

import calendar
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from app.models.plan import BillingInterval, Plan


def round_money(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_next_billing_date(
    anchor_date: date,
    from_date: date,
    interval: str,
    interval_count: int = 1,
) -> date:
    """
    Calculates the deterministic next billing anniversary date.
    Preserves calendar semantics and original anchor day (e.g. 31st),
    handling leap years and shorter months without repeated date drift.
    """
    if interval_count < 1:
        interval_count = 1

    interval_upper = interval.upper()

    if interval_upper == BillingInterval.DAILY.value:
        return from_date + timedelta(days=interval_count)

    elif interval_upper == BillingInterval.WEEKLY.value:
        return from_date + timedelta(weeks=interval_count)

    elif interval_upper == BillingInterval.MONTHLY.value:
        total_months = from_date.year * 12 + (from_date.month - 1) + interval_count
        target_year = total_months // 12
        target_month = (total_months % 12) + 1
        max_days = calendar.monthrange(target_year, target_month)[1]
        target_day = min(anchor_date.day, max_days)
        return date(target_year, target_month, target_day)

    elif interval_upper == BillingInterval.YEARLY.value:
        target_year = from_date.year + interval_count
        target_month = anchor_date.month
        max_days = calendar.monthrange(target_year, target_month)[1]
        target_day = min(anchor_date.day, max_days)
        return date(target_year, target_month, target_day)

    else:
        raise ValueError(f"Unsupported billing interval: '{interval}'")


def calculate_normalized_monthly_value(plan: Plan) -> Decimal:
    """
    Normalizes a plan's price to an estimated monthly recurring baseline
    to enable fair comparison across different intervals during plan changes.
    """
    price = Decimal(str(plan.price))
    count = Decimal(str(max(1, plan.interval_count)))
    interval = plan.billing_interval.upper()

    if interval == BillingInterval.MONTHLY.value:
        return (price / count).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    elif interval == BillingInterval.YEARLY.value:
        return (price / (Decimal("12") * count)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    elif interval == BillingInterval.WEEKLY.value:
        return ((price * Decimal("52")) / (Decimal("12") * count)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    elif interval == BillingInterval.DAILY.value:
        return ((price * Decimal("365")) / (Decimal("12") * count)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    else:
        return price
