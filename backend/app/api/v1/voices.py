import json
import logging
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import AuthenticatedUser, get_current_user
from app.database.session import get_db
from app.schemas.voice import VoiceCreate, VoiceListResponse, VoiceResponse, VoiceUpdate
from app.services.storage_service import storage_service
from app.services.voice_service import voice_service

logger = logging.getLogger("kolrep.api.voices")
router = APIRouter(tags=["Voices"])


@router.post("/uploads/presign")
async def get_presigned_upload(
    filename: str = Query(..., description="Original filename"),
    content_type: str = Query("audio/mpeg", description="MIME type"),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Generate a presigned upload URL for direct storage uploads."""
    ext = filename.split(".")[-1] if "." in filename else "mp3"
    object_key = f"uploads/{current_user.id}/{uuid.uuid4()}.{ext}"
    presigned = storage_service.get_presigned_upload_url(object_key, content_type)
    return presigned


@router.post("/voices", response_model=VoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_voice(
    file: UploadFile = File(...),
    name: str = Form(..., min_length=2, max_length=100),
    language: Optional[str] = Form("en"),
    speaker_relationship: str = Form("self"),
    transcript: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    consent_scope: Optional[str] = Form(None),
    terms_accepted: bool = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Upload an authorized voice sample, validate quality, record consent, and create clone."""
    parsed_scope = {"speech_generation": True}
    if consent_scope:
        try:
            parsed_scope = json.loads(consent_scope)
        except Exception:
            pass

    voice_payload = VoiceCreate(
        name=name,
        language=language,
        speaker_relationship=speaker_relationship,
        transcript=transcript,
        description=description,
        consent_scope=parsed_scope,
        terms_accepted=terms_accepted,
    )

    voice = await voice_service.process_and_create_voice(
        db=db,
        owner_id=current_user.id,
        file=file,
        voice_data=voice_payload,
    )
    return voice


@router.get("/voices", response_model=VoiceListResponse)
async def list_voices(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """List saved voice profiles for authenticated user."""
    items, total = await voice_service.get_user_voices(
        db=db, owner_id=current_user.id, page=page, limit=limit
    )
    return VoiceListResponse(items=items, total=total, page=page, limit=limit)


@router.get("/voices/{voice_id}", response_model=VoiceResponse)
async def get_voice(
    voice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Retrieve details of a specific voice profile."""
    voice = await voice_service.get_voice_by_id(db, voice_id, current_user.id)
    return voice


@router.patch("/voices/{voice_id}", response_model=VoiceResponse)
async def update_voice(
    voice_id: uuid.UUID,
    payload: VoiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Rename or update voice metadata."""
    voice = await voice_service.update_voice(db, voice_id, current_user.id, payload)
    return voice


@router.delete("/voices/{voice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_voice(
    voice_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """Delete a voice profile from provider and platform."""
    await voice_service.delete_voice(db, voice_id, current_user.id)
    return None
