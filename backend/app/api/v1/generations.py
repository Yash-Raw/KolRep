import logging
import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import AuthenticatedUser, get_current_user
from app.database.session import get_db
from app.schemas.generation import (
    GenerationCreate,
    GenerationListResponse,
    GenerationResponse,
)
from app.services.studio_service import studio_service
from app.services.storage_service import storage_service

logger = logging.getLogger("voicerep.api.generations")
router = APIRouter(tags=["Voice Studio"])


@router.post("/generations", response_model=GenerationResponse, status_code=status.HTTP_201_CREATED)
async def create_generation(
    payload: GenerationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Generate spoken speech from text using a saved cloned voice."""
    gen = await studio_service.create_generation(
        db=db,
        owner_id=current_user.id,
        payload=payload,
    )
    # Generate temporary audio URL for response
    audio_url = None
    if gen.audio_storage_key:
        try:
            audio_url = await studio_service.get_audio_url(db, gen.id, current_user.id)
        except Exception:
            pass

    response_data = GenerationResponse.model_validate(gen)
    response_data.audio_url = audio_url
    if gen.audio_storage_key:
        response_data.local_file_path = storage_service.get_local_path(gen.audio_storage_key)
    return response_data


@router.get("/generations", response_model=GenerationListResponse)
async def list_generations(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List generation history for authenticated user."""
    items, total = await studio_service.get_generations(
        db=db, owner_id=current_user.id, page=page, limit=limit
    )

    enriched_items: list[GenerationResponse] = []
    for item in items:
        resp = GenerationResponse.model_validate(item)
        if item.audio_storage_key:
            try:
                resp.audio_url = await studio_service.get_audio_url(db, item.id, current_user.id)
            except Exception:
                pass
            resp.local_file_path = storage_service.get_local_path(item.audio_storage_key)
        enriched_items.append(resp)

    return GenerationListResponse(items=enriched_items, total=total, page=page, limit=limit)


@router.get("/generations/{generation_id}", response_model=GenerationResponse)
async def get_generation(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve details of a single generation."""
    gen = await studio_service.get_generation_by_id(db, generation_id, current_user.id)
    resp = GenerationResponse.model_validate(gen)
    if gen.audio_storage_key:
        resp.audio_url = await studio_service.get_audio_url(db, gen.id, current_user.id)
        resp.local_file_path = storage_service.get_local_path(gen.audio_storage_key)
    return resp


@router.get("/generations/{generation_id}/audio")
async def get_generation_audio(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Get signed playback and download URL for generated audio."""
    url = await studio_service.get_audio_url(db, generation_id, current_user.id)
    return {"audio_url": url}


@router.delete("/generations/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a generation and its stored audio."""
    await studio_service.delete_generation(db, generation_id, current_user.id)
    return None
