from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.services import asset_service


router = APIRouter(prefix="/api/assets", tags=["assets"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _get_asset_or_404(db: Session, asset_id: UUID):
    asset = asset_service.get_asset_by_id(db, asset_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")
    return asset


@router.post("", response_model=AssetRead, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_roles("admin"))])
def create_asset(asset_data: AssetCreate, db: DatabaseSession):
    if asset_service.get_asset_by_code(db, asset_data.asset_code) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Asset code already exists")
    try:
        return asset_service.create_asset(db, asset_data)
    except asset_service.DuplicateAssetCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Asset code already exists") from exc


@router.get("", response_model=list[AssetRead])
def list_assets(
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    return asset_service.list_assets(db, skip=skip, limit=limit)


@router.get("/{asset_id}", response_model=AssetRead)
def get_asset(asset_id: UUID, db: DatabaseSession):
    return _get_asset_or_404(db, asset_id)


@router.patch("/{asset_id}", response_model=AssetRead,
              dependencies=[Depends(require_roles("admin"))])
def update_asset(asset_id: UUID, asset_data: AssetUpdate, db: DatabaseSession):
    asset = _get_asset_or_404(db, asset_id)
    if asset_data.asset_code is not None:
        existing_asset = asset_service.get_asset_by_code(db, asset_data.asset_code)
        if existing_asset is not None and existing_asset.id != asset.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Asset code already exists")
    try:
        return asset_service.update_asset(db, asset, asset_data)
    except asset_service.DuplicateAssetCodeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Asset code already exists") from exc


@router.delete("/{asset_id}", status_code=status.HTTP_204_NO_CONTENT,
               dependencies=[Depends(require_roles("admin"))])
def delete_asset(asset_id: UUID, db: DatabaseSession) -> Response:
    asset = _get_asset_or_404(db, asset_id)
    asset_service.delete_asset(db, asset)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
