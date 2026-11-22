import os
import shutil
import logging
from typing import Optional
import boto3
from botocore.config import Config
from app.core.config import settings

logger = logging.getLogger("kolrep.storage")


class StorageService:
    def __init__(self):
        self.is_r2_configured = bool(
            settings.R2_ACCESS_KEY_ID
            and settings.R2_SECRET_ACCESS_KEY
            and settings.R2_ENDPOINT_URL
        )
        self.bucket = settings.R2_BUCKET_NAME
        self.local_path = os.path.abspath(settings.LOCAL_STORAGE_PATH)

        if self.is_r2_configured:
            self.s3_client = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT_URL,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
        else:
            self.s3_client = None
            os.makedirs(self.local_path, exist_ok=True)
            logger.info(f"Using local storage path: {self.local_path}")

    def get_presigned_upload_url(
        self, object_key: str, content_type: str, expires_in: int = 3600
    ) -> dict[str, str]:
        if self.is_r2_configured:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": self.bucket,
                    "Key": object_key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_in,
            )
            return {"url": url, "key": object_key, "method": "PUT"}
        else:
            # Local fallback endpoint
            return {
                "url": f"{settings.BACKEND_URL}/api/v1/storage/upload/{object_key}",
                "key": object_key,
                "method": "POST",
            }

    def get_presigned_download_url(
        self, object_key: str, expires_in: int = 3600
    ) -> str:
        if self.is_r2_configured:
            return self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expires_in,
            )
        else:
            return f"{settings.BACKEND_URL}/api/v1/storage/download/{object_key}"

    def upload_bytes(
        self, data: bytes, object_key: str, content_type: str = "audio/mpeg"
    ) -> str:
        if self.is_r2_configured:
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=object_key,
                Body=data,
                ContentType=content_type,
            )
        else:
            dest = os.path.join(self.local_path, object_key)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(data)
        return object_key

    def upload_file(
        self, local_file_path: str, object_key: str, content_type: str = "audio/mpeg"
    ) -> str:
        if self.is_r2_configured:
            self.s3_client.upload_file(
                Filename=local_file_path,
                Bucket=self.bucket,
                Key=object_key,
                ExtraArgs={"ContentType": content_type},
            )
        else:
            dest = os.path.join(self.local_path, object_key)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copyfile(local_file_path, dest)
        return object_key

    def get_local_path(self, object_key: str) -> Optional[str]:
        """Returns the absolute filesystem path for local storage mode if available."""
        if self.is_r2_configured:
            return None

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

    def get_local_path_or_download(self, object_key: str, temp_dir: str = "/tmp") -> str:
        if not self.is_r2_configured:
            local = os.path.join(self.local_path, object_key)
            if os.path.exists(local):
                return local

        dest = os.path.join(temp_dir, os.path.basename(object_key))
        if self.is_r2_configured:
            self.s3_client.download_file(self.bucket, object_key, dest)
        return dest

    def delete_object(self, object_key: str) -> bool:
        try:
            if self.is_r2_configured:
                self.s3_client.delete_object(Bucket=self.bucket, Key=object_key)
            else:
                dest = os.path.join(self.local_path, object_key)
                if os.path.exists(dest):
                    os.remove(dest)
            return True
        except Exception as e:
            logger.error(f"Error deleting object {object_key}: {e}")
            return False


storage_service = StorageService()
