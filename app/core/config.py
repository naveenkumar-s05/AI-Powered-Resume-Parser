from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_env: str = "development"
    log_level: str = "INFO"
    app_name: str = "AI Resume Parser"
    api_v1_prefix: str = "/api/v1"
    auto_create_tables: bool = True

    secret_key: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    otp_secret: str = "change-me-otp-hmac-secret"
    otp_expire_seconds: int = 300
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60
    whatsapp_verification_required: bool = True

    totp_issuer: str = "AIResumeParser"
    totp_encryption_key: str = ""

    database_url: str = "postgresql+asyncpg://resume:resume@localhost:5432/resume_db"

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 5

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    whatsapp_api_url: str = "https://graph.facebook.com/v20.0"
    whatsapp_phone_number_id: str = ""
    whatsapp_access_token: str = ""
    whatsapp_otp_template: str = "otp_verification"
    whatsapp_template_lang: str = "en_US"
    whatsapp_otp_button_index: int = 0

    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() in {"development", "dev", "local"}

    @property
    def upload_path(self) -> Path:
        path = Path(self.upload_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
