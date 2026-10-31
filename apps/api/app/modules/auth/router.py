from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    DUMMY_PASSWORD_HASH
)

from app.core.config import settings

from app.core.dependencies import get_current_user

from app.models import User, UserRole, Customer

from app.modules.auth.schemas import (
    RegisterRequest,
    LoginRequest,
    RegisterResponse,
    LoginResponse,
    UserRead
)


router = APIRouter(
    prefix="/api/v1/auth",
    tags=["Authentication"]
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED
)
def register(
    payload: RegisterRequest,
    db: Session = Depends(get_db)
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

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.CUSTOMER.value,
        is_active=True
    )

    try:

        db.add(user)
        db.flush()

        customer = Customer(
            user_id=user.id,
            display_name=payload.display_name,
            company_name=payload.company_name,
            billing_email=(
                str(payload.billing_email).strip().lower()
                if payload.billing_email
                else email
            ),
            phone=payload.phone
        )

        db.add(customer)
        db.commit()

        db.refresh(user)
        db.refresh(customer)

        return RegisterResponse(
            user=user,
            customer=customer
        )

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists"
        )


@router.post(
    "/login",
    response_model=LoginResponse
)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db)
):

    email = str(payload.email).strip().lower()

    user = db.scalar(
        select(User).where(
            func.lower(User.email) == email
        )
    )

    if user is None:

        verify_password(
            payload.password,
            DUMMY_PASSWORD_HASH
        )

        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    if not verify_password(
        payload.password,
        user.password_hash
    ):

        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password"
        )

    if not user.is_active:

        raise HTTPException(
            status_code=403,
            detail="Your account is inactive"
        )

    token = create_access_token(str(user.id))

    return LoginResponse(
        access_token=token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user
    )


@router.get(
    "/me",
    response_model=UserRead
)
def get_profile(
    current_user: User = Depends(get_current_user)
):

    return current_user