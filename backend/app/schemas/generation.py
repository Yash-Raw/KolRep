from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, Field


class VoiceSettings(BaseModel):
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0)
    speed: float = Field(default=1.0, ge=0.5, le=2.0)
    style: float = Field(default=0.0, ge=0.0, le=1.0)


class GenerationCreate(BaseModel):
    voice_id: uuid.UUID
    input_text: str = Field(..., min_length=1, max_length=5000)
    model_id: str = Field(default="F5TTS_v1_Base")
    voice_settings: VoiceSettings = Field(default_factory=VoiceSettings)


class GenerationResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    voice_id: uuid.UUID
    input_text: str
    model_id: str
    voice_settings: dict[str, Any]
    status: str
    audio_storage_key: Optional[str] = None
    audio_url: Optional[str] = None
    local_file_path: Optional[str] = None
    character_count: int
    duration_seconds: Optional[float] = None
    error_code: Optional[str] = None
    is_watermarked: bool = True
    watermark_payload: Optional[dict[str, Any]] = None
    c2pa_manifest: Optional[dict[str, Any]] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class GenerationListResponse(BaseModel):
    items: list[GenerationResponse]
    total: int
    page: int
    limit: int
