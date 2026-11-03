import os
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from app.core.config import settings

router = APIRouter(prefix="/storage", tags=["Storage"])


@router.post("/upload/{file_path:path}")
async def upload_local_file(file_path: str, file: UploadFile = File(...)):
    """Local fallback endpoint for file uploads when R2 is not configured."""
    dest = os.path.join(os.path.abspath(settings.LOCAL_STORAGE_PATH), file_path)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    content = await file.read()
    with open(dest, "wb") as f:
        f.write(content)
    return {"status": "ok", "path": file_path}


@router.get("/download/{file_path:path}")
async def download_local_file(file_path: str):
    """Local fallback endpoint to stream/download audio files."""
    dest = os.path.join(os.path.abspath(settings.LOCAL_STORAGE_PATH), file_path)
    if not os.path.exists(dest):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(dest, media_type="audio/mpeg")
