from __future__ import annotations

from enum import Enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Index,
    String,
    column,
    func
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    CUSTOMER = "customer"


class User(UUIDTimestampMixin, Base):

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False
    )

    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=UserRole.CUSTOMER.value
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true"
    )

    customer_profile: Mapped["Customer | None"] = relationship(
        "Customer",
        back_populates="user",
        uselist=False
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'staff', 'customer')",
            name="ck_users_role"
        ),

        Index(
            "uq_users_email_lower",
            func.lower(column("email")),
            unique=True
        ),
    )

    def __repr__(self):
        return f"<User id={self.id} email={self.email} role={self.role}>"