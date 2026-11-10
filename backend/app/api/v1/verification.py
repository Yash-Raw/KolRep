import datetime
import hashlib
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.models.generation import Generation
from app.schemas.verification import VerificationReport
from app.services.c2pa_service import c2pa_service
from app.services.watermark_service import watermark_service

logger = logging.getLogger("voicerep.api.verification")

router = APIRouter(prefix="/verify", tags=["Deepfake & Provenance Verification"])


@router.post("", response_model=VerificationReport)
async def verify_audio(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Examines an uploaded audio file for:
    1. Layer 1: Out-of-band C2PA Cryptographic Provenance Manifest & X.509 signature.
    2. Layer 2: In-band Imperceptible Acoustic Watermark (QIM/Barker sync) directly from waveform.
    Cross-checks against generation records and returns a comprehensive authenticity report.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded audio file cannot be empty.",
        )

    # 1. Test Layer 1: C2PA Manifest extraction & signature validation
    c2pa_envelope = c2pa_service.extract_manifest(file_bytes)
    c2pa_valid = False
    c2pa_error = None
    manifest_data = None

    if c2pa_envelope:
        is_valid, sig_err = c2pa_service.verify_manifest_signature(c2pa_envelope)
        if is_valid:
            c2pa_valid = True
            manifest_data = c2pa_envelope.get("manifest")
        else:
            c2pa_error = sig_err or "Invalid cryptographic signature on C2PA manifest."
    else:
        c2pa_error = "No C2PA manifest container found (ID3v2 GEOB or RIFF c2pa missing)."

    # 2. Test Layer 2: In-band acoustic watermark extraction from PCM waveform
    acoustic_payload = watermark_service.extract_watermark_from_bytes(file_bytes)
    acoustic_detected = acoustic_payload is not None

    # Determine authenticity and tamper status
    is_authentic = c2pa_valid or acoustic_detected
    confidence = 0.0
    tamper_status = "unverified"

    if c2pa_valid and acoustic_detected:
        tamper_status = "fully_authentic"
        confidence = 1.0
    elif acoustic_detected and not c2pa_valid:
        tamper_status = "watermark_intact_metadata_stripped"
        confidence = 0.95
    elif c2pa_valid and not acoustic_detected:
        tamper_status = "c2pa_manifest_valid_short_audio"
        confidence = 0.85
    elif c2pa_envelope and not c2pa_valid:
        tamper_status = "tampered_signature_mismatch"
        confidence = 0.0

    # Extract metadata fields
    model_id = "F5TTS_v1_Base"
    timestamp = None
    created_at_iso = None
    generation_id = None
    user_hash = None
    license_text = "VoiceRep AI Synthetic Media Permissive License v1.0"
    compliance = [
        "EU AI Act Article 50 (Transparency and Watermarking of AI Generated Content)",
        "US Executive Order 14110 (Standards for AI-Generated Digital Content Provenance)",
    ]

    if manifest_data:
        instance_id = manifest_data.get("instance_id", "")
        if instance_id.startswith("urn:uuid:"):
            generation_id = instance_id.replace("urn:uuid:", "")

        for assertion in manifest_data.get("assertions", []):
            if assertion.get("label") == "c2pa.ai_generative_info":
                data = assertion.get("data", {})
                model_id = data.get("model_id", model_id)
                license_text = data.get("license", license_text)
                compliance = data.get("compliance", compliance)
                user_hash = data.get("owner_id_hash")

    if acoustic_payload:
        timestamp = acoustic_payload.get("timestamp")
        if timestamp:
            created_at_iso = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc).isoformat()
        if not user_hash:
            user_hash = acoustic_payload.get("user_hash")
        if not generation_id and acoustic_payload.get("gen_hash"):
            generation_id = f"gen_hash_{acoustic_payload.get('gen_hash')}"

    # If we have a generation UUID, try to query DB to verify against database record
    if generation_id and not generation_id.startswith("gen_hash_"):
        try:
            gen_uuid = uuid.UUID(generation_id)
            stmt = select(Generation).where(Generation.id == gen_uuid)
            res = await db.execute(stmt)
            gen_obj = res.scalar_one_or_none()
            if gen_obj:
                model_id = gen_obj.model_id
                if not created_at_iso and gen_obj.created_at:
                    created_at_iso = gen_obj.created_at.isoformat()
        except Exception:
            pass

    return VerificationReport(
        is_authentic=is_authentic,
        tamper_status=tamper_status,
        confidence_score=confidence,
        c2pa_valid=c2pa_valid,
        c2pa_manifest=manifest_data,
        c2pa_error=c2pa_error if not c2pa_valid else None,
        acoustic_watermark_detected=acoustic_detected,
        acoustic_payload=acoustic_payload,
        is_ai_generated=is_authentic,
        model_id=model_id if is_authentic else None,
        timestamp=timestamp,
        created_at_iso=created_at_iso,
        generation_id=generation_id,
        user_hash=user_hash,
        license=license_text if is_authentic else None,
        compliance=compliance if is_authentic else [],
    )


@router.get("/certificate/{generation_id}")
async def get_generation_certificate(
    generation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns the cryptographic provenance certificate and C2PA manifest for a specific generation.
    """
    stmt = select(Generation).where(Generation.id == generation_id)
    res = await db.execute(stmt)
    generation = res.scalar_one_or_none()
    if not generation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found.",
        )

    cert_pem = c2pa_service.get_public_certificate_pem()
    return {
        "generation_id": str(generation.id),
        "owner_id_hash": hashlib.sha256(str(generation.owner_id).encode("utf-8")).hexdigest(),
        "created_at": generation.created_at.isoformat() if generation.created_at else None,
        "is_watermarked": generation.is_watermarked,
        "watermark_payload": generation.watermark_payload,
        "c2pa_manifest": generation.c2pa_manifest,
        "certificate_pem": cert_pem,
        "signer": "VoiceRep Generation Signer CA (X.509 ECDSA P-256)",
        "compliance": [
            "EU AI Act Article 50",
            "US Executive Order 14110",
        ],
    }


@router.get("/public-key", response_class=PlainTextResponse)
async def get_public_certificate():
    """Returns VoiceRep's X.509 public signing certificate in PEM format for independent verification."""
    return c2pa_service.get_public_certificate_pem()
