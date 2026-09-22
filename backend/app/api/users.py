from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DatabaseSession, require_roles
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service


router = APIRouter(prefix="/api/users", tags=["users"],
                   dependencies=[Depends(require_roles("admin"))])


def _get_user_or_404(db: DatabaseSession, user_id: UUID):
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: DatabaseSession):
    if user_service.get_user_by_email(db, user_data.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")
    try:
        return user_service.create_user(db, user_data)
    except user_service.DuplicateUserEmailError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists") from exc


@router.get("", response_model=list[UserRead])
def list_users(db: DatabaseSession, skip: Annotated[int, Query(ge=0)] = 0,
               limit: Annotated[int, Query(ge=1, le=100)] = 100):
    return user_service.list_users(db, skip, limit)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: UUID, db: DatabaseSession):
    return _get_user_or_404(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(user_id: UUID, user_data: UserUpdate, db: DatabaseSession,
                current_user: CurrentUser):
    user = _get_user_or_404(db, user_id)
    if user.id == current_user.id and (user_data.is_active is False or
                                       (user_data.role is not None and user_data.role != "admin")):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail="Administrators cannot deactivate or demote their own account")
    return user_service.update_user(db, user, user_data)
