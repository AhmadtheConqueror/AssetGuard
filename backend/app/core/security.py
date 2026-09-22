from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

import jwt
from jwt import InvalidTokenError
from pwdlib import PasswordHash

from app.core.config import settings
from app.core.roles import UserRole, is_user_role


password_hash = PasswordHash.recommended()


class TokenValidationError(Exception):
    pass


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded_hash: str) -> bool:
    return password_hash.verify(password, encoded_hash)


def create_access_token(user_id: UUID, role: UserRole, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.AUTH_ACCESS_TOKEN_MINUTES)
    payload = {"sub": str(user_id), "role": role, "iat": issued_at, "exp": expires_at}
    return jwt.encode(
        payload,
        settings.AUTH_JWT_SECRET.get_secret_value(),
        algorithm=settings.AUTH_JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> tuple[UUID, UserRole]:
    try:
        payload = jwt.decode(
            token,
            settings.AUTH_JWT_SECRET.get_secret_value(),
            algorithms=[settings.AUTH_JWT_ALGORITHM],
            options={"require": ["sub", "role", "iat", "exp"]},
        )
        user_id = UUID(payload["sub"])
        role = payload["role"]
        if not isinstance(role, str) or not is_user_role(role):
            raise TokenValidationError
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise TokenValidationError from exc
    return user_id, cast(UserRole, role)
