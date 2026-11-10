import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, CompatibleJSON, GUID, utc_now


class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    voice_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("voices.id", ondelete="CASCADE"), nullable=False, index=True)
    input_text: Mapped[str] = mapped_column(Text, nullable=False)
    model_id: Mapped[str] = mapped_column(String(128), default="F5TTS_v1_Base", nullable=False)
    voice_settings: Mapped[dict[str, Any]] = mapped_column(CompatibleJSON(), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued", nullable=False, index=True)
    audio_storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    provider_request_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    character_count: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_code: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_watermarked: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    watermark_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(CompatibleJSON(), nullable=True)
    c2pa_manifest: Mapped[Optional[dict[str, Any]]] = mapped_column(CompatibleJSON(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    owner = relationship("User", back_populates="generations")
    voice = relationship("Voice", back_populates="generations")

    __table_args__ = (
        Index("ix_generations_owner_created", "owner_id", "created_at"),
    )
