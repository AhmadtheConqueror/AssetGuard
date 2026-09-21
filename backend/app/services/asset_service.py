from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetUpdate


class DuplicateAssetCodeError(Exception):
    pass


def create_asset(db: Session, asset_data: AssetCreate) -> Asset:
    asset = Asset(**asset_data.model_dump())
    db.add(asset)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateAssetCodeError from exc
    db.refresh(asset)
    return asset


def get_asset_by_id(db: Session, asset_id: UUID) -> Asset | None:
    return db.get(Asset, asset_id)


def get_asset_by_code(db: Session, asset_code: str) -> Asset | None:
    statement = select(Asset).where(Asset.asset_code == asset_code)
    return db.scalar(statement)


def list_assets(db: Session, skip: int = 0, limit: int = 100) -> list[Asset]:
    statement = select(Asset).order_by(Asset.created_at, Asset.id).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def update_asset(db: Session, asset: Asset, asset_data: AssetUpdate) -> Asset:
    for field_name, value in asset_data.model_dump(exclude_unset=True).items():
        setattr(asset, field_name, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateAssetCodeError from exc
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset: Asset) -> None:
    db.delete(asset)
    db.commit()
