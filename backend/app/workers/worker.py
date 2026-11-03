import asyncio
import logging
import uuid
from arq.connections import RedisSettings
from app.core.config import settings
from app.database.session import AsyncSessionLocal
from app.models.generation import Generation
from app.schemas.generation import GenerationCreate, VoiceSettings
from app.services.studio_service import studio_service

logger = logging.getLogger("voicerep.worker")


async def generate_speech_task(ctx, generation_id: str, owner_id: str, text: str, voice_id: str, settings_dict: dict, model_id: str):
    logger.info(f"Worker picked up speech generation job {generation_id}")
    async with AsyncSessionLocal() as db:
        payload = GenerationCreate(
            voice_id=uuid.UUID(voice_id),
            input_text=text,
            model_id=model_id,
            voice_settings=VoiceSettings(**settings_dict),
        )
        try:
            await studio_service.create_generation(
                db=db,
                owner_id=uuid.UUID(owner_id),
                payload=payload,
            )
            logger.info(f"Worker completed speech generation job {generation_id}")
        except Exception as e:
            logger.error(f"Worker failed on speech generation {generation_id}: {e}")
            raise


class WorkerSettings:
    functions = [generate_speech_task]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
