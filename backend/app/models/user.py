import uuid
from datetime import datetime
from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base, GUID, utc_now


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    voices = relationship("Voice", back_populates="owner", cascade="all, delete-orphan")
    consents = relationship("VoiceConsent", back_populates="owner", cascade="all, delete-orphan")
    generations = relationship("Generation", back_populates="owner", cascade="all, delete-orphan")
