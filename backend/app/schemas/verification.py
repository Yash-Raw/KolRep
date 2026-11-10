from typing import Any, Optional
from pydantic import BaseModel


class VerificationReport(BaseModel):
    is_authentic: bool
    tamper_status: str
    confidence_score: float
    c2pa_valid: bool
    c2pa_manifest: Optional[dict[str, Any]] = None
    c2pa_error: Optional[str] = None
    acoustic_watermark_detected: bool
    acoustic_payload: Optional[dict[str, Any]] = None
    is_ai_generated: bool
    model_id: Optional[str] = None
    timestamp: Optional[int] = None
    created_at_iso: Optional[str] = None
    generation_id: Optional[str] = None
    user_hash: Optional[str] = None
    license: Optional[str] = None
    compliance: list[str] = []
