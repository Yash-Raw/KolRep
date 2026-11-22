import logging
import os
import subprocess
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.generation import Generation
from app.models.voice import Voice
from app.providers import get_voice_provider, self_hosted_provider
from app.schemas.generation import GenerationCreate
from app.services.audio_service import FFMPEG_BIN, audio_service
from app.services.c2pa_service import c2pa_service
from app.services.storage_service import storage_service
from app.services.watermark_service import watermark_service

logger = logging.getLogger("kolrep.studio_service")


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

            # 1. Embed imperceptible acoustic watermark (in-band protection)
            acoustic_payload = None
            try:
                watermarked_bytes, acoustic_payload = watermark_service.embed_watermark_in_bytes(
                    audio_bytes=audio_bytes,
                    owner_id=str(owner_id),
                    generation_id=str(gen_id),
                    is_mp3=True,
                )
            except Exception as wm_err:
                logger.warning(f"Acoustic watermarking fallback: {wm_err}")
                if audio_bytes.startswith(b"RIFF"):
                    # Transcode pristine WAV to 256k MP3
                    tmp_wav = f"/tmp/fallback_{gen_id}.wav"
                    tmp_mp3 = f"/tmp/fallback_{gen_id}.mp3"
                    try:
                        with open(tmp_wav, "wb") as f:
                            f.write(audio_bytes)
                        subprocess.run(
                            [
                                FFMPEG_BIN,
                                "-y",
                                "-i", tmp_wav,
                                "-c:a", "libmp3lame",
                                "-b:a", "256k",
                                "-ar", "24000",
                                tmp_mp3,
                            ],
                            check=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                        )
                        with open(tmp_mp3, "rb") as f:
                            watermarked_bytes = f.read()
                    except Exception:
                        watermarked_bytes = audio_bytes
                    finally:
                        if os.path.exists(tmp_wav):
                            os.remove(tmp_wav)
                        if os.path.exists(tmp_mp3):
                            os.remove(tmp_mp3)
                else:
                    watermarked_bytes = audio_bytes

            # 2. Cryptographically sign C2PA manifest & embed into media container (out-of-band provenance)
            signed_envelope = None
            try:
                protected_audio_bytes, signed_envelope = c2pa_service.sign_and_embed(
                    audio_bytes=watermarked_bytes,
                    generation_id=str(gen_id),
                    owner_id=str(owner_id),
                    voice_id=str(voice.id),
                    model_id=payload.model_id,
                    acoustic_payload=acoustic_payload,
                    is_mp3=True,
                )
            except Exception as c2pa_err:
                logger.warning(f"C2PA manifest embedding fallback: {c2pa_err}")
                protected_audio_bytes = watermarked_bytes

            # Save protected audio in object storage
            storage_service.upload_bytes(protected_audio_bytes, storage_key, content_type="audio/mpeg")

            # Measure audio duration
            temp_path = f"/tmp/{gen_id}.mp3"
            with open(temp_path, "wb") as f:
                f.write(protected_audio_bytes)
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
            generation.is_watermarked = bool(acoustic_payload is not None)
            generation.watermark_payload = acoustic_payload
            generation.c2pa_manifest = signed_envelope.get("manifest") if signed_envelope else None
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
        return storage_service.get_download_url(gen.audio_storage_key)

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
