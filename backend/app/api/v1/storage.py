import os
from typing import Optional
from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status
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


@router.api_route("/download/{file_path:path}", methods=["GET", "HEAD"])
async def download_local_file(
    file_path: str,
    download: bool = Query(False, description="Set True to force Content-Disposition attachment"),
    filename: Optional[str] = Query(None, description="Custom filename for attachment download"),
):
    """
    Local fallback endpoint to stream/download audio files.
    Supports HTTP 206 Partial Content / Range requests for smooth scrubbing.
    """
    dest = get_safe_storage_path(settings.LOCAL_STORAGE_PATH, file_path)
    if not os.path.exists(dest) or not os.path.isfile(dest):
        # Fallback check across root/backend storage locations
        alt_dirs = [
            os.path.abspath(os.path.join(settings.LOCAL_STORAGE_PATH, "..", "storage")),
            os.path.abspath(os.path.join(settings.LOCAL_STORAGE_PATH, "backend", "storage")),
            os.path.abspath(os.path.join(".", "storage")),
            os.path.abspath(os.path.join("..", "storage")),
        ]
        found = False
        for alt_dir in alt_dirs:
            try:
                alt_dest = get_safe_storage_path(alt_dir, file_path)
                if os.path.exists(alt_dest) and os.path.isfile(alt_dest):
                    dest = alt_dest
                    found = True
                    break
            except Exception:
                continue
        if not found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    media_type = guess_media_type(dest)
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "public, max-age=3600",
    }

    if download or filename:
        save_filename = filename or os.path.basename(dest)
        return FileResponse(
            dest,
            media_type=media_type,
            filename=save_filename,
            content_disposition_type="attachment",
            headers=headers,
        )

    return FileResponse(
        dest,
        media_type=media_type,
        headers=headers,
    )
