import re


def validate_password_policy(password: str) -> str:

    if len(password) <= 8:
        raise ValueError("Password must contain more than 8 characters.")

    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain an uppercase letter.")

    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain a lowercase letter.")

    if not re.search(r"[^\w\s]", password):
        raise ValueError("Password must contain a special character.")

    if len(password) > 128:
        raise ValueError("Password cannot exceed 128 characters.")

    return password