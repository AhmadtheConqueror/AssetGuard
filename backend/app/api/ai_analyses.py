from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.ai.base import (
    AIAnalyzerConfigurationError,
    AIAnalyzerResponseError,
    AIAnalyzerUnavailableError,
)
from app.db.session import get_db
from app.schemas.ai_analysis import AIAnalysisRead
from app.services import ai_analysis_service


router = APIRouter(tags=["AI analyses"])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _asset_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")


@router.post(
    "/api/assets/{asset_id}/ai-analyses",
    response_model=AIAnalysisRead,
    status_code=status.HTTP_201_CREATED,
)
def create_ai_analysis(
    asset_id: UUID,
    db: DatabaseSession,
    limit_per_sensor: Annotated[int, Query(ge=2, le=500)] = 50,
):
    try:
        return ai_analysis_service.create_ai_analysis(db, asset_id, limit_per_sensor)
    except ai_analysis_service.AssetNotFoundError as exc:
        raise _asset_not_found() from exc
    except ai_analysis_service.InsufficientTelemetryError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except (AIAnalyzerConfigurationError, AIAnalyzerUnavailableError) as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except AIAnalyzerResponseError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/api/assets/{asset_id}/ai-analyses", response_model=list[AIAnalysisRead])
def list_ai_analyses(
    asset_id: UUID,
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    try:
        return ai_analysis_service.list_ai_analyses(db, asset_id, skip, limit)
    except ai_analysis_service.AssetNotFoundError as exc:
        raise _asset_not_found() from exc


@router.get("/api/assets/{asset_id}/ai-analyses/latest", response_model=AIAnalysisRead)
def get_latest_ai_analysis(asset_id: UUID, db: DatabaseSession):
    try:
        analysis = ai_analysis_service.get_latest_ai_analysis(db, asset_id)
    except ai_analysis_service.AssetNotFoundError as exc:
        raise _asset_not_found() from exc
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset has no AI analyses")
    return analysis


@router.get("/api/ai-analyses/{analysis_id}", response_model=AIAnalysisRead)
def get_ai_analysis(analysis_id: UUID, db: DatabaseSession):
    analysis = ai_analysis_service.get_ai_analysis_by_id(db, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI analysis not found")
    return analysis
