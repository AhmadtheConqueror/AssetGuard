from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.alert import AlertCreate, AlertRead, AlertResolveRequest, AlertUpdate
from app.schemas.asset import AssetCreate, AssetRead, AssetUpdate
from app.schemas.condition_assessment import ConditionAssessmentRead
from app.schemas.sensor import SensorCreate, SensorRead, SensorUpdate
from app.schemas.sensor_reading import SensorReadingCreate, SensorReadingRead

__all__ = [
    "AIAnalysisRead",
    "AlertCreate",
    "AlertRead",
    "AlertResolveRequest",
    "AlertUpdate",
    "AssetCreate",
    "AssetRead",
    "AssetUpdate",
    "ConditionAssessmentRead",
    "SensorCreate",
    "SensorRead",
    "SensorUpdate",
    "SensorReadingCreate",
    "SensorReadingRead",
]
