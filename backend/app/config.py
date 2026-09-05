from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "RazControl AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    DATABASE_URL: str = (
        "postgresql://razcontrol:razcontrol@localhost:5432/razcontrol"
    )

    ANOMALY_MIN_HISTORY: int = 5
    ANOMALY_IQR_MULTIPLIER: float = 1.5
    ANOMALY_MIN_RISK_SCORE: float = 60.0
    ANOMALY_USE_ML: bool = False

    INVESTIGATION_PROVIDER: str = "evidence_only"
    PIPELINE_MAX_INVESTIGATIONS: int = 50
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
