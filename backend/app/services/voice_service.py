import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from fastapi import HTTPException, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.models.voice import Voice
from app.models.voice_consent import VoiceConsent
from app.providers.elevenlabs import elevenlabs_provider
from app.schemas.audio import AudioQualityReport
from app.schemas.voice import VoiceCreate, VoiceUpdate
from app.services.audio_service import audio_service
from app.services.storage_service import storage_service

logger = logging.getLogger("voicerep.voice_service")


class VoiceService:
    async def process_and_create_voice(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        file: UploadFile,
        voice_data: VoiceCreate,
    ) -> Voice:
        # Check upload size limit
        file_bytes = await file.read()
        if len(file_bytes) > settings.max_upload_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File exceeds maximum upload size of {settings.MAX_UPLOAD_SIZE_MB}MB.",
            )

        if not voice_data.terms_accepted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You must accept the terms of use and confirm speaker consent.",
            )

        # Save temporarily for ffmpeg validation
        ext = os.path.splitext(file.filename or "")[1].lower() or ".mp3"
        temp_input = f"/tmp/upload_{uuid.uuid4()}{ext}"
        try:
            with open(temp_input, "wb") as f:
                f.write(file_bytes)

            # Validate audio
            try:
                report: AudioQualityReport = audio_service.analyze_audio_stream(temp_input)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=str(e),
                )

            if not report.is_clonable:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Audio quality insufficient for cloning: {', '.join(report.warnings)}",
                )

            # Normalize/convert audio to standard clean WAV
            temp_wav = audio_service.extract_or_convert_to_wav(temp_input)

            # Store original sample in storage
            sample_key = f"samples/{owner_id}/{uuid.uuid4()}{ext}"
            storage_service.upload_bytes(file_bytes, sample_key, content_type=file.content_type or "audio/mpeg")

            # Create Voice record in DB
            voice = Voice(
                id=uuid.uuid4(),
                owner_id=owner_id,
                name=voice_data.name.strip(),
                provider="elevenlabs",
                status="cloning",
                language=voice_data.language or "en",
                audio_duration=report.duration_seconds,
                quality_report=report.model_dump(),
                sample_storage_key=sample_key,
            )
            db.add(voice)

            # Record Consent
            consent = VoiceConsent(
                id=uuid.uuid4(),
                voice_id=voice.id,
                owner_id=owner_id,
                speaker_relationship=voice_data.speaker_relationship,
                consent_scope=voice_data.consent_scope,
                terms_version="v1.0",
                consent_status="granted",
                evidence_storage_key=sample_key,
            )
            db.add(consent)
            await db.commit()
            await db.refresh(voice)

            # Perform cloning with ElevenLabs
            try:
                clone_res = await elevenlabs_provider.create_voice(
                    name=voice.name,
                    audio_file_path=temp_wav,
                    description=f"Cloned for VoiceRep user {owner_id}",
                    remove_background_noise=False,
                )
                voice.provider_voice_id = clone_res.get("voice_id")
                if clone_res.get("requires_verification"):
                    voice.status = "verification_required"
                else:
                    voice.status = "ready"

            except Exception as e:
                logger.error(f"Voice cloning provider failure: {e}")
                voice.status = "failed"
                await db.commit()
                await db.refresh(voice)
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Voice cloning provider error: {str(e)}",
                )

            await db.commit()
            await db.refresh(voice)
            return voice

        finally:
            if os.path.exists(temp_input):
                os.remove(temp_input)
            if "temp_wav" in locals() and os.path.exists(temp_wav):
                os.remove(temp_wav)

    async def get_user_voices(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Voice], int]:
        offset = (page - 1) * limit
        query = (
            select(Voice)
            .where(Voice.owner_id == owner_id, Voice.deleted_at.is_(None))
            .order_by(Voice.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = select(func.count(Voice.id)).where(
            Voice.owner_id == owner_id, Voice.deleted_at.is_(None)
        )

        res = await db.execute(query)
        items = list(res.scalars().all())

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total

    async def get_voice_by_id(
        self,
        db: AsyncSession,
        voice_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Voice:
        query = select(Voice).where(
            Voice.id == voice_id,
            Voice.owner_id == owner_id,
            Voice.deleted_at.is_(None),
        )
        res = await db.execute(query)
        voice = res.scalar_one_or_none()
        if not voice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Voice profile not found or access denied.",
            )
        return voice

    async def update_voice(
        self,
        db: AsyncSession,
        voice_id: uuid.UUID,
        owner_id: uuid.UUID,
        update_data: VoiceUpdate,
    ) -> Voice:
        voice = await self.get_voice_by_id(db, voice_id, owner_id)
        if update_data.name is not None:
            voice.name = update_data.name.strip()
        if update_data.language is not None:
            voice.language = update_data.language
        await db.commit()
        await db.refresh(voice)
        return voice

    async def delete_voice(
        self,
        db: AsyncSession,
        voice_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> bool:
        voice = await self.get_voice_by_id(db, voice_id, owner_id)

        # Mark as deleting
        voice.status = "deleting"
        await db.commit()

        # Delete from provider
        if voice.provider_voice_id:
            try:
                await elevenlabs_provider.delete_voice(voice.provider_voice_id)
            except Exception as e:
                logger.warning(f"Could not delete provider voice: {e}")

        # Delete sample file if stored
        if voice.sample_storage_key:
            storage_service.delete_object(voice.sample_storage_key)

        # Mark soft deleted
        voice.deleted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        voice.status = "deleted"
        await db.commit()
        return True


voice_service = VoiceService()
