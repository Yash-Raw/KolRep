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
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/voicerep"
    SYNC_DATABASE_URL: Optional[str] = None

    # Voice Provider Configuration (100% self-hosted local engine)
    VOICE_PROVIDER: str = "self_hosted"

    # Self-Hosted Voice Engine Settings
    SELF_HOSTED_MODEL: str = "F5TTS_v1_Base"
    SELF_HOSTED_DEVICE: str = "auto"
    SELF_HOSTED_VOICE_DIR: str = "./storage/voice_profiles"
    SELF_HOSTED_NFE_STEPS: int = 36

    # Gemini (Optional Analysis)
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-3.8-flash"

    # Storage (Cloudflare R2 / S3)
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY_ID: Optional[str] = None
    R2_SECRET_ACCESS_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "voicerep-audio"
    R2_ENDPOINT_URL: Optional[str] = None
    LOCAL_STORAGE_PATH: str = "./storage"
    STORAGE_LOCAL_DIR: Optional[str] = None

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Upload configuration
    MAX_UPLOAD_SIZE_MB: int = 50
    MAX_AUDIO_DURATION_SECONDS: int = 300

    # Desktop Application Mode (Native macOS deployment)
    VOICEREP_DESKTOP_MODE: bool = False
    DESKTOP_DATA_DIR: Optional[str] = None
    ENABLE_REDIS: bool = True

    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def model_post_init(self, __context) -> None:
        if self.VOICEREP_DESKTOP_MODE:
            base_dir = Path(self.DESKTOP_DATA_DIR) if self.DESKTOP_DATA_DIR else (Path.home() / "Library" / "Application Support" / "VoiceRep")
            self.DESKTOP_DATA_DIR = str(base_dir)
            
            # Switch database to SQLite if not explicitly set to something non-default
            if "postgresql" in self.DATABASE_URL:
                db_path = base_dir / "database" / "voicerep.db"
                self.DATABASE_URL = f"sqlite+aiosqlite:///{db_path}"
                self.SYNC_DATABASE_URL = f"sqlite:///{db_path}"
            
            # Switch local storage and voice profiles to desktop data directory
            if self.LOCAL_STORAGE_PATH == "./storage":
                self.LOCAL_STORAGE_PATH = str(base_dir / "storage")
            if self.SELF_HOSTED_VOICE_DIR == "./storage/voice_profiles":
                self.SELF_HOSTED_VOICE_DIR = str(base_dir / "storage" / "voice_profiles")
            
            # Disable Redis in desktop mode
            self.ENABLE_REDIS = False
        
        self.STORAGE_LOCAL_DIR = self.LOCAL_STORAGE_PATH

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
