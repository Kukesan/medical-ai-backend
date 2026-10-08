from functools import lru_cache
from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PRODUCTION_ENVS = {"prod", "production"}
MIN_JWT_SECRET_LENGTH = 32
PLACEHOLDER_SECRETS = {"change-me", "change-me-too", "secret", "changeme"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Yarlit Medical AI Backend", alias="APP_NAME")
    app_env: str = Field(default="dev", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    api_v1_prefix: str = Field(default="/api/v1", alias="API_V1_PREFIX")

    # Comma-separated browser origins allowed to call the API, e.g. "https://envagai.com,https://www.envagai.com".
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    # Proxy IPs whose X-Forwarded-For header is trusted for the client IP (rate limiting). Railway's edge
    # proxy addresses are not fixed, so "*" is the practical value there.
    forwarded_allow_ips: str = Field(default="127.0.0.1", alias="FORWARDED_ALLOW_IPS")

    database_url: str = Field(alias="DATABASE_URL")

    jwt_secret_key: str = Field(alias="JWT_SECRET_KEY")
    jwt_refresh_secret_key: str = Field(alias="JWT_REFRESH_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    # Hard limit since the user last typed their password; refreshing cannot extend a session past this.
    session_max_age_days: int = Field(default=30, alias="SESSION_MAX_AGE_DAYS")

    internal_service_api_key: str = Field(default="", alias="INTERNAL_SERVICE_API_KEY")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1-mini", alias="OPENAI_MODEL")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimensions: int = Field(default=1536, alias="EMBEDDING_DIMENSIONS")

    local_storage_dir: str = Field(default="storage", alias="LOCAL_STORAGE_DIR")
    log_dir: str = Field(default="logs", alias="LOG_DIR")
    error_log_retention_days: int = Field(default=30, alias="ERROR_LOG_RETENTION_DAYS")
    max_upload_size_mb: int = Field(default=25, alias="MAX_UPLOAD_SIZE_MB")
    rate_limit: str = Field(default="100/minute", alias="RATE_LIMIT")

    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="us-east-1", alias="AWS_REGION")
    s3_bucket_name: str = Field(default="", alias="S3_BUCKET_NAME")
    presigned_url_expire_seconds: int = Field(default=900, alias="PRESIGNED_URL_EXPIRE_SECONDS")

    google_places_api_key: str = Field(default="", alias="GOOGLE_PLACES_API_KEY")

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in PRODUCTION_ENVS

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _require_strong_secrets_in_production(self) -> "Settings":
        if not self.is_production:
            return self
        for name, value in (
            ("JWT_SECRET_KEY", self.jwt_secret_key),
            ("JWT_REFRESH_SECRET_KEY", self.jwt_refresh_secret_key),
        ):
            if value.lower() in PLACEHOLDER_SECRETS or len(value) < MIN_JWT_SECRET_LENGTH:
                raise ValueError(f"{name} must be a random value of at least {MIN_JWT_SECRET_LENGTH} characters in production")
        if self.jwt_secret_key == self.jwt_refresh_secret_key:
            raise ValueError("JWT_SECRET_KEY and JWT_REFRESH_SECRET_KEY must differ")
        if "*" in self.cors_origin_list:
            raise ValueError("CORS_ORIGINS must list explicit origins in production")
        return self

    @property
    def local_storage_path(self) -> Path:
        path = Path(self.local_storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def log_path(self) -> Path:
        path = Path(self.log_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
