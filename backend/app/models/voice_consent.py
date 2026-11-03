import uuid
from datetime import datetime
from typing import Any, Optional
from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, CompatibleJSON, GUID, utc_now


class VoiceConsent(Base):
    __tablename__ = "voice_consents"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    voice_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("voices.id", ondelete="CASCADE"), nullable=False, index=True)
    owner_id: Mapped[uuid.UUID] = mapped_column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    speaker_relationship: Mapped[str] = mapped_column(String(64), nullable=False)
    consent_scope: Mapped[dict[str, Any]] = mapped_column(CompatibleJSON(), nullable=False)
    terms_version: Mapped[str] = mapped_column(String(32), default="v1.0", nullable=False)
    consent_status: Mapped[str] = mapped_column(String(32), default="granted", nullable=False, index=True)
    evidence_storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    consented_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    owner = relationship("User", back_populates="consents")
    voice = relationship("Voice", back_populates="consents")

    __table_args__ = (
        Index("ix_consents_voice_owner", "voice_id", "owner_id"),
    )
