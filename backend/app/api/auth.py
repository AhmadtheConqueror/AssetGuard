from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.schemas.auth import LoginRequest, LogoutResponse, TokenResponse
from app.schemas.user import UserRead
from app.services import user_service


router = APIRouter(prefix="/api/auth", tags=["authentication"])


def _invalid_login() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                         detail="Invalid email or password",
                         headers={"WWW-Authenticate": "Bearer"})


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: DatabaseSession):
    user = user_service.get_user_by_email(db, login_data.email)
    if user is None or not verify_password(login_data.password, user.password_hash) or not user.is_active:
        raise _invalid_login()
    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.id, user.role),
                         expires_in=settings.AUTH_ACCESS_TOKEN_MINUTES * 60,
                         user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def get_me(current_user: CurrentUser):
    return current_user


@router.post("/logout", response_model=LogoutResponse)
def logout(_: CurrentUser):
    # Tokens are stateless in this phase; clients discard the bearer token on logout.
    return LogoutResponse()
