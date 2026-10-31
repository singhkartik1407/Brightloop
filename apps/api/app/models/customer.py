import uuid

from sqlalchemy import (
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
    CheckConstraint
)

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDTimestampMixin


class Customer(UUIDTimestampMixin, Base):

    __tablename__ = "customers"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        unique=True
    )

    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    company_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True
    )

    billing_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False
    )

    phone: Mapped[str | None] = mapped_column(
        String(30),
        nullable=True
    )

    tax_identifier: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True
    )

    billing_address_line1: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    billing_address_line2: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True
    )

    billing_city: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    billing_state: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True
    )

    billing_postal_code: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True
    )

    billing_country_code: Mapped[str | None] = mapped_column(
        String(2),
        nullable=True
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    user: Mapped["User | None"] = relationship(
        "User",
        back_populates="customer_profile"
    )

    __table_args__ = (
        CheckConstraint(
            "length(trim(display_name)) > 0",
            name="ck_customers_display_name_nonempty"
        ),

        Index(
            "ix_customers_billing_email",
            "billing_email"
        ),
    )

    def __repr__(self):
        return f"<Customer id={self.id} name={self.display_name}>"