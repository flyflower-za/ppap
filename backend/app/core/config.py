from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List
from pydantic import field_validator


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "PPAP File Verification Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    API_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://ppap:ppap123@localhost:5432/ppap"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT / Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # SSO / LDAP (future)
    SSO_ENABLED: bool = False
    SSO_PROVIDER: Optional[str] = None
    LDAP_URL: Optional[str] = None

    # File Storage
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "ppap-files"
    MINIO_SECURE: bool = False

    # File Upload Limits
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # Legacy Aliyun AI Configuration (DEPRECATED - Use System Settings > AI Model Configuration instead)
    # These environment variables are kept for backward compatibility only
    # All new LLM configurations should be done through the web UI: System Settings > AI Model Configuration
    ALIYUN_ACCESS_KEY_ID: Optional[str] = None  # Deprecated: Use database model profiles instead
    ALIYUN_ACCESS_KEY_SECRET: Optional[str] = None  # Deprecated: Not used for OpenAI-compatible APIs
    ALIYUN_AGENT_ENDPOINT: Optional[str] = None  # Deprecated: Use database model profiles instead
    ALIYUN_MODEL_NAME: Optional[str] = "gpt-3.5-turbo"  # Deprecated: Use database model profiles instead

    # Email / SMTP
    SMTP_ENABLED: bool = False
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 465
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None
    SMTP_USE_TLS: bool = True

    # File Retention
    FILE_RETENTION_DAYS: int = 30

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
