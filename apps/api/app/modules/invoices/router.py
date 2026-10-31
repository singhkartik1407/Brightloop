from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.invoice import Invoice, InvoiceStatus
from app.models.user import User, UserRole
from app.modules.invoices.schemas import (
    InvoiceCancelRequest,
    InvoiceCreate,
    InvoiceResponse,
)
from app.modules.invoices.services import (
    assert_invoice_access,
    cancel_invoice,
    confirm_invoice,
    create_manual_invoice,
    get_invoice_pdf_bytes,
    get_user_customer_id,
    send_invoice,
    serialize_invoice,
)


router = APIRouter(prefix="/api/v1/invoices", tags=["Invoices"])


@router.get("", response_model=dict[str, Any])
def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status_filter: InvoiceStatus | None = Query(None, alias="status"),
    customer_id: uuid.UUID | None = Query(None, alias="customerId"),
    overdue_only: bool | None = Query(None, alias="overdueOnly"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    query = select(Invoice)

    # Customer isolation
    if current_user.role not in (UserRole.ADMIN.value, UserRole.STAFF.value):
        cust_id = get_user_customer_id(current_user)
        if not cust_id:
            return {"items": [], "total": 0, "page": page, "pageSize": page_size}
        query = query.where(Invoice.customer_id == cust_id)
    elif customer_id:
        query = query.where(Invoice.customer_id == customer_id)

    if status_filter:
        query = query.where(Invoice.status == status_filter.value)

    if overdue_only:
        today = date.today()
        query = query.where(
            Invoice.due_date < today,
            Invoice.amount_due > 0,
            Invoice.status.notin_([InvoiceStatus.PAID.value, InvoiceStatus.CANCELLED.value]),
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    invoices = (
        db.scalars(
            query.order_by(Invoice.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        .all()
    )

    return {
        "items": [serialize_invoice(inv).model_dump(by_alias=True) for inv in invoices],
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    invoice = create_manual_invoice(db, payload, current_user)
    return serialize_invoice(invoice)


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "INVOICE_NOT_FOUND", "message": "Invoice not found"},
        )
    assert_invoice_access(invoice, current_user)
    return serialize_invoice(invoice)


@router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
def confirm_invoice_endpoint(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    invoice = confirm_invoice(db, invoice_id, current_user)
    return serialize_invoice(invoice)


@router.post("/{invoice_id}/cancel", response_model=InvoiceResponse)
def cancel_invoice_endpoint(
    invoice_id: uuid.UUID,
    payload: InvoiceCancelRequest | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InvoiceResponse:
    reason = payload.reason if payload else None
    invoice = cancel_invoice(db, invoice_id, reason, current_user)
    return serialize_invoice(invoice)


@router.post("/{invoice_id}/send", status_code=status.HTTP_202_ACCEPTED)
def send_invoice_endpoint(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    send_invoice(db, invoice_id, current_user)
    return {"message": "Invoice delivery queued."}


@router.get("/{invoice_id}/pdf")
def download_invoice_pdf(
    invoice_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    pdf_bytes = get_invoice_pdf_bytes(db, invoice_id, current_user)
    invoice = db.get(Invoice, invoice_id)
    filename = f"{invoice.invoice_number if invoice else 'invoice'}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
