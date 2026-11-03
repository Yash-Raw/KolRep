from typing import Optional
from pydantic import BaseModel, Field


class AudioQualityReport(BaseModel):
    duration_seconds: float = Field(..., description="Duration of audio in seconds")
    format: str = Field(..., description="Detected audio format / container")
    sample_rate: int = Field(..., description="Sample rate in Hz")
    channels: int = Field(..., description="Number of audio channels")
    quality: str = Field(..., description="Overall quality assessment (good, acceptable, poor)")
    speech_ratio: Optional[float] = Field(None, description="Estimated speech-to-silence ratio")
    has_clipping: bool = Field(False, description="Whether audio clipping / distortion was detected")
    warnings: list[str] = Field(default_factory=list, description="Quality warnings if any")
    recommendation: str = Field(..., description="Usage recommendation")
    is_clonable: bool = Field(..., description="Whether audio meets criteria for instant cloning")
