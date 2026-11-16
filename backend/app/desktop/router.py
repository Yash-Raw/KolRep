import asyncio
import os
import platform
import shutil
import torch
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from app.core.config import settings
from app.desktop.job_manager import local_job_manager
from app.desktop.model_manager import model_manager
from app.services.audio_service import FFMPEG_BIN, FFPROBE_BIN

router = APIRouter(prefix="/desktop", tags=["Desktop System"])


@router.get("/status")
async def get_desktop_status():
    """
    Returns system diagnostic status, hardware acceleration information,
    bundled audio tools status, and neural model availability.
    """
    # Detect Apple Silicon hardware acceleration
    has_mps = torch.backends.mps.is_available()
    device = "mps" if has_mps else "cpu"

    # FFmpeg status
    ffmpeg_available = bool(FFMPEG_BIN and os.path.exists(FFMPEG_BIN))
    ffprobe_available = bool(FFPROBE_BIN and os.path.exists(FFPROBE_BIN))

    # Neural model status
    model_status = model_manager.check_model_availability()

    return {
        "platform": platform.platform(),
        "arch": platform.machine(),
        "is_apple_silicon": platform.machine() == "arm64",
        "device": device,
        "mps_available": has_mps,
        "ffmpeg": {
            "available": ffmpeg_available,
            "path": FFMPEG_BIN,
        },
        "ffprobe": {
            "available": ffprobe_available,
            "path": FFPROBE_BIN,
        },
        "models": model_status,
        "download": model_manager.get_download_status(),
        "active_jobs": len([j for j in local_job_manager.list_jobs() if j["status"] == "processing"]),
    }


@router.post("/download-models")
async def trigger_model_download(background_tasks: BackgroundTasks):
    """
    Triggers asynchronous download of missing neural models into
    persistent application storage.
    """
    status_info = model_manager.get_download_status()
    if status_info["is_downloading"]:
        return {"status": "already_downloading", "progress": status_info["progress"]}

    async def _download_task():
        try:
            await model_manager.download_required_models()
        except Exception:
            pass

    asyncio.create_task(_download_task())
    return {"status": "started", "message": "Model download initiated in background."}


@router.get("/download-status")
async def get_model_download_status():
    """Returns real-time model download progress and errors."""
    return model_manager.get_download_status()


@router.get("/jobs")
async def list_desktop_jobs(limit: int = 50):
    """Returns local job queue status for desktop voice studio."""
    return {"jobs": local_job_manager.list_jobs(limit=limit)}


@router.post("/jobs/{job_id}/cancel")
async def cancel_desktop_job(job_id: str):
    """Cancels a queued or processing generation job."""
    success = await local_job_manager.cancel_job(job_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found or already finished.",
        )
    return {"status": "cancelled", "job_id": job_id}
