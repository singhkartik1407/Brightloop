from uuid import UUID
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status
)

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.models import Customer, User, UserRole

from app.modules.customers.schemas import (
    CustomerCreateRequest,
    CustomerUpdateRequest,
    CustomerSelfUpdateRequest,
    CustomerRead,
    CustomerProfileRead,
    CustomerListResponse
)


router = APIRouter(
    prefix="/api/v1/customers",
    tags=["Customer Management"]
)

# Reusable permission dependencies
admin_staff = require_roles(UserRole.ADMIN, UserRole.STAFF)
customer_only = require_roles(UserRole.CUSTOMER)


# ----------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------

def get_customer_or_404(db: Session, customer_id: UUID):

    customer = db.get(Customer, customer_id)

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    return customer


def get_own_customer(db: Session, user: User):

    customer = db.scalar(
        select(Customer).where(
            Customer.user_id == user.id,
            Customer.is_active.is_(True)
        )
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer profile not found"
        )

    return customer


def save_customer(db: Session, customer: Customer):

    try:
        db.commit()
        db.refresh(customer)
        return customer

    except IntegrityError:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Customer operation failed due to a data conflict"
        )


def normalize_email(value):

    return str(value).strip().lower()


# ----------------------------------------
# CUSTOMER PORTAL: OWN PROFILE
# Keep /me before /{customer_id}
# ----------------------------------------

@router.get(
    "/me",
    response_model=CustomerProfileRead,
    tags=["Customer Portal"]
)
def get_my_customer(
    db: Session = Depends(get_db),
    user: User = Depends(customer_only)
):

    return get_own_customer(db, user)


@router.patch(
    "/me",
    response_model=CustomerProfileRead,
    tags=["Customer Portal"]
)
def update_my_customer(
    payload: CustomerSelfUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(customer_only)
):

    customer = get_own_customer(db, user)

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    if "billing_email" in changes:
        changes["billing_email"] = normalize_email(
            changes["billing_email"]
        )

    for field, value in changes.items():
        setattr(customer, field, value)

    return save_customer(db, customer)


# ----------------------------------------
# CREATE CUSTOMER
# ADMIN / STAFF
# ----------------------------------------

@router.post(
    "",
    response_model=CustomerRead,
    status_code=status.HTTP_201_CREATED
)
def create_customer(
    payload: CustomerCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff)
):

    data = payload.model_dump()

    data["billing_email"] = normalize_email(
        data["billing_email"]
    )

    customer = Customer(**data)

    db.add(customer)

    return save_customer(db, customer)


# ----------------------------------------
# LIST / SEARCH / PAGINATION
# ADMIN / STAFF
# ----------------------------------------

@router.get(
    "",
    response_model=CustomerListResponse
)
def list_customers(
    q: str | None = Query(default=None, max_length=200),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff)
):

    conditions = []

    if not include_inactive:
        conditions.append(
            Customer.is_active.is_(True)
        )

    search = (q or "").strip()

    if search:

        # Escape SQL LIKE wildcard characters so searches are literal.
        escaped = (
            search
            .replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

        pattern = f"%{escaped}%"

        conditions.append(
            or_(
                Customer.display_name.ilike(pattern, escape="\\"),
                Customer.company_name.ilike(pattern, escape="\\"),
                Customer.billing_email.ilike(pattern, escape="\\")
            )
        )

    total = db.scalar(
        select(func.count(Customer.id)).where(*conditions)
    ) or 0

    customers = db.scalars(
        select(Customer)
        .where(*conditions)
        .order_by(
            Customer.created_at.desc(),
            Customer.id
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()

    pages = (total + page_size - 1) // page_size

    return CustomerListResponse(
        items=customers,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


# ----------------------------------------
# GET CUSTOMER DETAILS
# ADMIN / STAFF
# ----------------------------------------

@router.get(
    "/{customer_id}",
    response_model=CustomerRead
)
def get_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff)
):

    return get_customer_or_404(db, customer_id)


# ----------------------------------------
# UPDATE CUSTOMER
# ADMIN / STAFF
# ----------------------------------------

@router.patch(
    "/{customer_id}",
    response_model=CustomerRead
)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff)
):

    customer = get_customer_or_404(db, customer_id)

    if not customer.is_active:
        raise HTTPException(
            status_code=409,
            detail="Archived customer must be restored before updating"
        )

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=400,
            detail="No fields provided for update"
        )

    if "billing_email" in changes:
        changes["billing_email"] = normalize_email(
            changes["billing_email"]
        )

    for field, value in changes.items():
        setattr(customer, field, value)

    return save_customer(db, customer)


# ----------------------------------------
# ARCHIVE CUSTOMER (SOFT DELETE)
# ADMIN / STAFF
# ----------------------------------------

@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def archive_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff)
):

    customer = get_customer_or_404(db, customer_id)

    if customer.is_active:
        customer.is_active = False
        db.commit()

    return Response(status_code=204)


# ----------------------------------------
# RESTORE ARCHIVED CUSTOMER
# ADMIN / STAFF
# ----------------------------------------

@router.post(
    "/{customer_id}/restore",
    response_model=CustomerRead
)
def restore_customer(
    customer_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(admin_staff)
):

    customer = get_customer_or_404(db, customer_id)

    if not customer.is_active:
        customer.is_active = True
        return save_customer(db, customer)

    return customer
