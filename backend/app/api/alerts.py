from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.schemas.alert import (
    AlertCreate,
    AlertRead,
    AlertResolveRequest,
    AlertSeverity,
    AlertStatus,
    AlertUpdate,
)
from app.services import alert_service


router = APIRouter(tags=["alerts"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _get_alert_or_404(db: Session, alert_id: UUID):
    alert = alert_service.get_alert_by_id(db, alert_id)
    if alert is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found")
    return alert


@router.post(
    "/api/assets/{asset_id}/alerts",
    response_model=AlertRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles("engineer", "admin"))],
)
def create_alert(asset_id: UUID, alert_data: AlertCreate, db: DatabaseSession):
    try:
        return alert_service.create_alert(db, asset_id, alert_data)
    except alert_service.AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found") from exc
    except alert_service.AIAnalysisNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI analysis not found") from exc
    except alert_service.AIAnalysisAssetConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="AI analysis belongs to a different Asset",
        ) from exc


@router.get("/api/assets/{asset_id}/alerts", response_model=list[AlertRead])
def list_alerts(
    asset_id: UUID,
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    alert_status: Annotated[AlertStatus | None, Query(alias="status")] = None,
    severity: AlertSeverity | None = None,
):
    try:
        return alert_service.list_alerts_for_asset(
            db,
            asset_id,
            skip=skip,
            limit=limit,
            alert_status=alert_status,
            severity=severity,
        )
    except alert_service.AssetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found") from exc


@router.get("/api/alerts/{alert_id}", response_model=AlertRead)
def get_alert(alert_id: UUID, db: DatabaseSession):
    return _get_alert_or_404(db, alert_id)


@router.patch("/api/alerts/{alert_id}", response_model=AlertRead,
              dependencies=[Depends(require_roles("engineer", "admin"))])
def update_alert(alert_id: UUID, alert_data: AlertUpdate, db: DatabaseSession):
    alert = _get_alert_or_404(db, alert_id)
    return alert_service.update_alert(db, alert, alert_data)


@router.post("/api/alerts/{alert_id}/acknowledge", response_model=AlertRead,
             dependencies=[Depends(require_roles("technician", "engineer", "admin"))])
def acknowledge_alert(alert_id: UUID, db: DatabaseSession):
    alert = _get_alert_or_404(db, alert_id)
    try:
        return alert_service.acknowledge_alert(db, alert)
    except alert_service.InvalidAlertTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/api/alerts/{alert_id}/resolve", response_model=AlertRead,
             dependencies=[Depends(require_roles("engineer", "admin"))])
def resolve_alert(alert_id: UUID, resolve_data: AlertResolveRequest, db: DatabaseSession):
    alert = _get_alert_or_404(db, alert_id)
    return alert_service.resolve_alert(db, alert, resolve_data)
