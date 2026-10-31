from getpass import getpass

from pydantic import EmailStr, TypeAdapter, ValidationError

from sqlalchemy import select, func
from sqlalchemy.exc import IntegrityError

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.core.password_policy import validate_password_policy

from app.models import User, UserRole


def main():

    with SessionLocal() as db:

        existing_admin = db.scalar(
            select(User.id).where(
                User.role == UserRole.ADMIN.value
            )
        )

        if existing_admin:

            print("An administrator already exists.")
            return

        email_input = input("Admin email: ").strip()

        try:

            email = str(
                TypeAdapter(EmailStr).validate_python(email_input)
            ).lower()

        except ValidationError:

            print("Invalid email address.")
            return

        password = getpass("Admin password: ")
        confirm = getpass("Confirm password: ")

        if password != confirm:

            print("Passwords do not match.")
            return

        try:
            validate_password_policy(password)

        except ValueError as error:

            print(str(error))
            return

        existing_user = db.scalar(
            select(User.id).where(
                func.lower(User.email) == email
            )
        )

        if existing_user:

            print("A user with this email already exists.")
            return

        admin = User(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.ADMIN.value,
            is_active=True
        )

        try:

            db.add(admin)
            db.commit()

            print("Administrator created successfully.")

        except IntegrityError:

            db.rollback()
            print("Unable to create administrator. Email may already exist.")


if __name__ == "__main__":
    main()