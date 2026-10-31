from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_roles
from app.core.security import hash_password

from app.models import User, UserRole

from app.modules.auth.schemas import UserRead
from app.modules.users.schemas import StaffCreateRequest


router = APIRouter(
    prefix="/api/v1/admin",
    tags=["Admin - Staff Management"]
)


@router.post(
    "/staff",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED
)
def create_staff(
    payload: StaffCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles(UserRole.ADMIN))
):

    email = str(payload.email).strip().lower()

    existing_user = db.scalar(
        select(User.id).where(
            func.lower(User.email) == email
        )
    )

    if existing_user:

        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )

    staff = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.STAFF.value,
        is_active=True
    )

    try:

        db.add(staff)
        db.commit()
        db.refresh(staff)

        return staff

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="Unable to create staff account"
        )