from datetime import datetime, timedelta, timezone

import jwt

from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()

# Used when an email does not exist, to reduce timing differences.
DUMMY_PASSWORD_HASH = password_hash.hash(
    "DummyPassword#NeverUsed123"
)


def hash_password(password: str) -> str:

    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    try:
        return password_hash.verify(
            plain_password,
            hashed_password
        )
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str) -> str:

    now = datetime.now(timezone.utc)

    expires = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": expires
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )