import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    APP_SECRET_KEY: str = "change-this-insecure-secret-key-for-dev-only-32bytesmin"
    ORGANIZATION_ID: str = "ORG_DEMO_01"
    DEFAULT_TIMEZONE: str = "America/New_York"
    MAX_UPLOAD_SIZE_MB: int = 200

    # Database
    DATABASE_URL: str = "sqlite:///./hr_audit.db"

    # MinIO / Object Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET_RECEIPTS: str = "hr-receipts"
    MINIO_BUCKET_PACKS: str = "hr-audit-packs"

    # Service & Auth
    N8N_SERVICE_API_KEY: str = "n8n_secret_service_token_dev_placeholder"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 480
    GOOGLE_CLIENT_ID: Optional[str] = None
    POSH_ENCRYPTION_KEY: str = "9kITcpy5f5xwWB0f9uqA1CCjDcLA_EdevoGJSROIJQc="

    # Email & Verification (OTP)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@hraudit.local"
    OTP_EXPIRATION_MINUTES: int = 10
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 60
    AUTH_RATE_LIMIT_PER_MINUTE: int = 10

    # Optional Crustdata
    CRUSTDATA_ENABLED: bool = False
    CRUSTDATA_API_KEY: str = "crustdata_key_placeholder"
    CRUSTDATA_BASE_URL: str = "https://api.crustdata.com"

    # AI / LLM Explainers (Phase 9: Provider-agnostic gemini | anthropic | none)
    LLM_PROVIDER: str = "none"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-haiku-20240307"

    # Seeding demo data (opt-in only, default False)
    SEED_DEMO_DATA: bool = False


settings = Settings()
