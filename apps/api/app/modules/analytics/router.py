from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User, UserRole
from app.modules.analytics.schemas import (
    DashboardSummary,
    RevenueSeriesResponse,
)
from app.modules.analytics.services import (
    get_dashboard_summary,
    get_overdue_invoices_list,
    get_revenue_series,
    get_upcoming_renewals_list,
)


router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


def assert_analytics_access(current_user: User) -> None:
    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "FORBIDDEN", "message": "Access restricted to staff and administrators"},
        )


@router.get("/summary", response_model=DashboardSummary)
def get_summary(
    from_date: date | None = Query(None, alias="from"),
    to_date: date | None = Query(None, alias="to"),
    currency: str = Query("INR"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummary:
    assert_analytics_access(current_user)
    return get_dashboard_summary(
        db=db,
        from_date=from_date,
        to_date=to_date,
        currency=currency,
    )


@router.get("/revenue", response_model=RevenueSeriesResponse)
def get_revenue(
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    group_by: str = Query("MONTH", alias="groupBy"),
    currency: str = Query("INR"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RevenueSeriesResponse:
    assert_analytics_access(current_user)
    return get_revenue_series(
        db=db,
        from_date=from_date,
        to_date=to_date,
        group_by=group_by,
        currency=currency,
    )


@router.get("/renewals", response_model=dict[str, Any])
def get_renewals(
    days: int = Query(30, ge=1, le=365),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    assert_analytics_access(current_user)
    items, total = get_upcoming_renewals_list(
        db=db,
        days=days,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [item.model_dump(by_alias=True) for item in items],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/overdue", response_model=dict[str, Any])
def get_overdue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    assert_analytics_access(current_user)
    items, total = get_overdue_invoices_list(
        db=db,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [item.model_dump(by_alias=True) for item in items],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }
