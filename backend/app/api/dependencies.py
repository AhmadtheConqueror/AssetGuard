from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.roles import UserRole
from app.core.security import TokenValidationError, decode_access_token
from app.db.session import get_db
from app.models.user import User
from app.services import user_service


bearer_scheme = HTTPBearer(auto_error=False)
DatabaseSession = Annotated[Session, Depends(get_db)]
BearerCredentials = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]


def _credentials_error() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                         detail="Could not validate credentials",
                         headers={"WWW-Authenticate": "Bearer"})


def get_current_user(credentials: BearerCredentials, db: DatabaseSession) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_error()
    try:
        user_id, _ = decode_access_token(credentials.credentials)
    except TokenValidationError as exc:
        raise _credentials_error() from exc
    user = user_service.get_user_by_id(db, user_id)
    if user is None or not user.is_active:
        raise _credentials_error()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[CurrentUser], User]:
    allowed_roles = set(roles)

    def role_dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail="You do not have permission to perform this action")
        return current_user

    return role_dependency
