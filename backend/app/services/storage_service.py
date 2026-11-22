import os
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger("kolrep.storage")


class StorageService:
    """Manages local filesystem storage for voice samples and generated audio."""

    def __init__(self):
        self.local_path = os.path.abspath(settings.LOCAL_STORAGE_PATH)
        os.makedirs(self.local_path, exist_ok=True)
        logger.info(f"Using local storage path: {self.local_path}")

    def get_download_url(self, object_key: str) -> str:
        """Returns the local backend download/stream URL for an audio object."""
        return f"{settings.BACKEND_URL}/api/v1/storage/download/{object_key}"

    def upload_bytes(
        self, data: bytes, object_key: str, content_type: str = "audio/mpeg"
    ) -> str:
        """Writes audio bytes to local storage and returns the storage key."""
        dest = os.path.join(self.local_path, object_key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as f:
            f.write(data)
        return object_key

    def get_local_path(self, object_key: str) -> Optional[str]:
        """Returns the absolute filesystem path for a local storage object."""
        # Check default path
        direct = os.path.abspath(os.path.join(self.local_path, object_key))
        if os.path.exists(direct):
            return direct

        # Check alternate relative directory locations (e.g. workspace root vs backend/)
        alt1 = os.path.abspath(os.path.join(self.local_path, "..", "storage", object_key))
        if os.path.exists(alt1):
            return alt1

        alt2 = os.path.abspath(os.path.join(self.local_path, "backend", "storage", object_key))
        if os.path.exists(alt2):
            return alt2

        return direct

    def delete_object(self, object_key: str) -> bool:
        """Deletes a stored object from local storage if it exists."""
        try:
            dest = os.path.join(self.local_path, object_key)
            if os.path.exists(dest):
                os.remove(dest)
            return True
        except Exception as e:
            logger.error(f"Error deleting object {object_key}: {e}")
            return False


storage_service = StorageService()
