from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.schemas.condition_assessment import ConditionAssessmentRead
from app.services import condition_assessment_service


router = APIRouter(tags=["condition assessments"], dependencies=[Depends(get_current_user)])
DatabaseSession = Annotated[Session, Depends(get_db)]


def _asset_not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")


@router.post(
    "/api/assets/{asset_id}/condition-assessments",
    response_model=ConditionAssessmentRead,
    dependencies=[Depends(require_roles("engineer", "admin"))],
)
def evaluate_condition(asset_id: UUID, db: DatabaseSession):
    try:
        return condition_assessment_service.evaluate_asset(db, asset_id)
    except condition_assessment_service.AssetNotFoundError as exc:
        raise _asset_not_found() from exc
    except condition_assessment_service.NoTelemetryError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get(
    "/api/assets/{asset_id}/condition-assessments",
    response_model=list[ConditionAssessmentRead],
)
def list_condition_assessments(
    asset_id: UUID,
    db: DatabaseSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    try:
        return condition_assessment_service.list_assessments(db, asset_id, skip, limit)
    except condition_assessment_service.AssetNotFoundError as exc:
        raise _asset_not_found() from exc


@router.get(
    "/api/assets/{asset_id}/condition-assessments/latest",
    response_model=ConditionAssessmentRead,
)
def get_latest_condition_assessment(asset_id: UUID, db: DatabaseSession):
    try:
        assessment = condition_assessment_service.get_latest_assessment(db, asset_id)
    except condition_assessment_service.AssetNotFoundError as exc:
        raise _asset_not_found() from exc
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset has no condition assessments")
    return assessment


@router.get(
    "/api/condition-assessments/{assessment_id}",
    response_model=ConditionAssessmentRead,
)
def get_condition_assessment(assessment_id: UUID, db: DatabaseSession):
    assessment = condition_assessment_service.get_assessment_by_id(db, assessment_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition assessment not found")
    return assessment
