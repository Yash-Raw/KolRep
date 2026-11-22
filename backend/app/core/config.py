from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
_ROOT_DIR = _BACKEND_DIR.parent
_ENV_FILES = [
    str(_ROOT_DIR / ".env"),
    str(_BACKEND_DIR / ".env"),
    ".env",
]


class Settings(BaseSettings):
    APP_ENV: str = "development"
    APP_SECRET_KEY: str = "dev-secret-key-for-local-development-only-32chars"
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/kolrep"
    SYNC_DATABASE_URL: Optional[str] = None

    # Voice Provider Configuration (100% self-hosted local engine)
    VOICE_PROVIDER: str = "self_hosted"

    # Self-Hosted Voice Engine Settings
    SELF_HOSTED_MODEL: str = "F5TTS_v1_Base"
    SELF_HOSTED_DEVICE: str = "auto"
    SELF_HOSTED_VOICE_DIR: str = "./storage/voice_profiles"
    SELF_HOSTED_NFE_STEPS: int = 32

    # Gemini (Optional Analysis)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # Storage (Cloudflare R2 / S3)
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "kolrep-audio"
    R2_ENDPOINT_URL: Optional[str] = None
    LOCAL_STORAGE_PATH: str = "./storage"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Upload configuration
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_AUDIO_DURATION_SECONDS: int = 300

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
