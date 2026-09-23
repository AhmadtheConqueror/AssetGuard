from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    DATABASE_URL: str
    GEMINI_API_KEY: SecretStr | None = None
    GEMINI_MODEL: str = "gemini-3.8-flash"
    GEMINI_FALLBACK_MODEL: str = "gemini-3.6-flash"
    AUTH_JWT_SECRET: SecretStr
    AUTH_JWT_ALGORITHM: str = "HS256"
    AUTH_ACCESS_TOKEN_MINUTES: int = 60
    INGESTION_API_KEY: SecretStr | None = None
    # Statistical sensitivity settings, not OEM limits or safety thresholds.
    MONITORING_MIN_HISTORY: int = 12
    MONITORING_BASELINE_WINDOW: int = 30
    MONITORING_RECENT_WINDOW: int = 5
    MONITORING_TREND_WINDOW: int = 8
    MONITORING_WATCH_THRESHOLD: float = 3.0
    MONITORING_DEVIATION_THRESHOLD: float = 5.0
    MONITORING_TREND_THRESHOLD: float = 2.5
    MONITORING_PERSISTENCE_RATIO: float = 0.6
    MONITORING_MIN_SCALE_RATIO: float = 0.005
    MONITORING_MIN_ABSOLUTE_SCALE: float = 0.000001
    # Workflow sensitivity settings, not OEM alarm or equipment safety limits.
    ALERTING_ENABLED: bool = True
    ALERT_ANOMALOUS_ASSESSMENTS_REQUIRED: int = 2
    ALERT_COOLDOWN_MINUTES: int = 60
    AUTO_AI_ESCALATION_ENABLED: bool = False

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
