import os
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from app.core.config import settings

router = APIRouter(prefix="/storage", tags=["Storage"])


def get_safe_storage_path(base_dir: str, rel_path: str) -> str:
    """
    Resolves and verifies that rel_path stays strictly within base_dir.
    Raises HTTPException(403) if path traversal is attempted.
    """
    clean_rel = rel_path.lstrip("/").replace("\\", "/")
    base_abs = os.path.abspath(base_dir)
    full_path = os.path.abspath(os.path.join(base_abs, clean_rel))

    # Strict boundary containment check
    if os.path.commonpath([full_path, base_abs]) != base_abs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Directory traversal path detected.",
        )
    return full_path


def guess_media_type(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".wav":
        return "audio/wav"
    elif ext == ".mp3":
        return "audio/mpeg"
    elif ext in (".webm", ".weba"):
        return "audio/webm"
    elif ext == ".m4a":
        return "audio/mp4"
    elif ext == ".ogg":
        return "audio/ogg"
    return "application/octet-stream"


@router.post("/upload/{file_path:path}")
async def upload_local_file(file_path: str, file: UploadFile = File(...)):
    """Local fallback endpoint for file uploads when R2 is not configured."""
    dest = get_safe_storage_path(settings.LOCAL_STORAGE_PATH, file_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {"status": "ok", "path": file_path}


@router.get("/download/{file_path:path}")
async def download_local_file(file_path: str):
    """
    Local fallback endpoint to stream/download audio files.
    Supports HTTP 206 Partial Content / Range requests for smooth scrubbing.
    """
    dest = get_safe_storage_path(settings.LOCAL_STORAGE_PATH, file_path)
    if not os.path.exists(dest) or not os.path.isfile(dest):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    media_type = guess_media_type(dest)
    return FileResponse(
        dest,
        media_type=media_type,
        headers={
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=3600",
        },
    )
