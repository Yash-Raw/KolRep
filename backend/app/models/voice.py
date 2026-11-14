import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, CompatibleJSON, GUID, utc_now


class Voice(Base):
    __tablename__ = "voices"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider: Mapped[str] = mapped_column(String(64), default="self_hosted", nullable=False)
    provider_voice_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(64), default="upload_pending", nullable=False, index=True)
    language: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    audio_duration: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quality_report: Mapped[Optional[dict[str, Any]]] = mapped_column(CompatibleJSON(), nullable=True)
    sample_storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    owner = relationship("User", back_populates="voices")
    consents = relationship("VoiceConsent", back_populates="voice", cascade="all, delete-orphan")
    generations = relationship("Generation", back_populates="voice", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_voices_owner_status", "owner_id", "status"),
    )
