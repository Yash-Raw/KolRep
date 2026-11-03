from datetime import datetime
from typing import Any, Optional
import uuid
from pydantic import BaseModel, Field
from app.schemas.audio import AudioQualityReport


class VoiceConsentCreate(BaseModel):
    speaker_relationship: str = Field(..., description="'self' or 'authorized_representative'")
    consent_scope: dict[str, bool] = Field(
        default_factory=lambda: {"speech_generation": True, "ai_agent": True},
        description="Allowed use cases"
    )
    terms_accepted: bool = Field(..., description="Must accept terms of use and consent policy")
    terms_version: str = Field(default="v1.0")


class VoiceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    language: Optional[str] = Field(default="en", max_length=32)
    speaker_relationship: str = Field(default="self")
    consent_scope: dict[str, bool] = Field(
        default_factory=lambda: {"speech_generation": True, "ai_agent": True}
    )
    terms_accepted: bool = Field(default=True)


class VoiceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    language: Optional[str] = Field(None, max_length=32)


class VoiceConsentResponse(BaseModel):
    id: uuid.UUID
    voice_id: uuid.UUID
    speaker_relationship: str
    consent_scope: dict[str, Any]
    terms_version: str
    consent_status: str
    consented_at: datetime
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class VoiceResponse(BaseModel):
    id: uuid.UUID
    owner_id: uuid.UUID
    name: str
    provider: str
    provider_voice_id: Optional[str] = None
    status: str
    language: Optional[str] = None
    audio_duration: Optional[float] = None
    quality_report: Optional[dict[str, Any]] = None
    sample_storage_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class VoiceListResponse(BaseModel):
    items: list[VoiceResponse]
    total: int
    page: int
    limit: int
