import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.generation import Generation
from app.models.voice import Voice
from app.providers import elevenlabs_provider, get_voice_provider, self_hosted_provider
from app.schemas.generation import GenerationCreate
from app.services.audio_service import audio_service
from app.services.storage_service import storage_service

logger = logging.getLogger("voicerep.studio_service")


class StudioService:
    async def create_generation(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        payload: GenerationCreate,
    ) -> Generation:
        # Check voice ownership and ready status
        voice_query = select(Voice).where(
            Voice.id == payload.voice_id,
            Voice.owner_id == owner_id,
            Voice.deleted_at.is_(None),
        )
        voice_res = await db.execute(voice_query)
        voice = voice_res.scalar_one_or_none()
        if not voice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected voice profile not found or access denied.",
            )

        if voice.status != "ready" or not voice.provider_voice_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Voice is not ready for generation (current status: {voice.status}).",
            )

        text = payload.input_text.strip()
        if not text:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Input text cannot be empty.",
            )

        char_count = len(text)
        gen_id = uuid.uuid4()

        generation = Generation(
            id=gen_id,
            owner_id=owner_id,
            voice_id=voice.id,
            input_text=text,
            model_id=payload.model_id,
            voice_settings=payload.voice_settings.model_dump(),
            status="processing",
            character_count=char_count,
        )
        db.add(generation)
        await db.commit()
        await db.refresh(generation)

        # Call active voice provider TTS
        storage_key = f"generations/{owner_id}/{gen_id}.mp3"
        try:
            active_provider = get_voice_provider(voice.provider)
            audio_bytes = await active_provider.synthesize(
                voice_id=voice.provider_voice_id,
                text=text,
                settings=payload.voice_settings.model_dump(),
                model_id=payload.model_id,
            )

            # Save in object storage
            storage_service.upload_bytes(audio_bytes, storage_key, content_type="audio/mpeg")

            # Measure audio duration
            temp_path = f"/tmp/{gen_id}.mp3"
            with open(temp_path, "wb") as f:
                f.write(audio_bytes)
            try:
                info = audio_service.probe_file(temp_path)
                dur = float(info.get("format", {}).get("duration", 0.0))
            except Exception:
                dur = None
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

            generation.status = "completed"
            generation.audio_storage_key = storage_key
            generation.duration_seconds = dur
            generation.completed_at = datetime.now(timezone.utc).replace(tzinfo=None)

        except Exception as e:
            logger.error(f"Generation synthesis failed: {e}")
            generation.status = "failed"
            generation.error_code = str(e)[:255]
            await db.commit()
            await db.refresh(generation)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Speech synthesis error: {str(e)}",
            )

        await db.commit()
        await db.refresh(generation)
        return generation

    async def get_generations(
        self,
        db: AsyncSession,
        owner_id: uuid.UUID,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[Generation], int]:
        offset = (page - 1) * limit
        query = (
            select(Generation)
            .where(Generation.owner_id == owner_id)
            .order_by(Generation.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        count_query = select(func.count(Generation.id)).where(Generation.owner_id == owner_id)

        res = await db.execute(query)
        items = list(res.scalars().all())

        count_res = await db.execute(count_query)
        total = count_res.scalar() or 0

        return items, total

    async def get_generation_by_id(
        self,
        db: AsyncSession,
        generation_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> Generation:
        query = select(Generation).where(
            Generation.id == generation_id,
            Generation.owner_id == owner_id,
        )
        res = await db.execute(query)
        gen = res.scalar_one_or_none()
        if not gen:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generation not found or access denied.",
            )
        return gen

    async def get_audio_url(
        self,
        db: AsyncSession,
        generation_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> str:
        gen = await self.get_generation_by_id(db, generation_id, owner_id)
        if not gen.audio_storage_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Audio file is not available for this generation.",
            )
        return storage_service.get_presigned_download_url(gen.audio_storage_key)

    async def delete_generation(
        self,
        db: AsyncSession,
        generation_id: uuid.UUID,
        owner_id: uuid.UUID,
    ) -> bool:
        gen = await self.get_generation_by_id(db, generation_id, owner_id)
        if gen.audio_storage_key:
            storage_service.delete_object(gen.audio_storage_key)
        await db.delete(gen)
        await db.commit()
        return True


studio_service = StudioService()
