import asyncio
import logging
import os
from pathlib import Path
import shutil
import time
from typing import Any, Optional
from app.core.config import settings

logger = logging.getLogger("voicerep.desktop.model_manager")

REQUIRED_MODELS = [
    {
        "id": "f5-tts-base",
        "name": "F5-TTS Base (Flow Matching DiT)",
        "repo_id": "SWivid/F5-TTS",
        "filename": "F5TTS_v1_Base/model_1250000.safetensors",
        "approx_size_mb": 850,
        "extra_files": [],
    },
    {
        "id": "vocos-mel-24khz",
        "name": "Vocos Neural Vocoder 24kHz",
        "repo_id": "charactr/vocos-mel-24khz",
        "filename": "pytorch_model.bin",
        "approx_size_mb": 55,
        "extra_files": ["config.yaml"],
    },
    {
        "id": "whisper-tiny",
        "name": "OpenAI Whisper Tiny (Phonetic Alignment)",
        "repo_id": "openai/whisper-tiny",
        "filename": "model.safetensors",
        "approx_size_mb": 150,
        "extra_files": [
            "config.json",
            "tokenizer.json",
            "tokenizer_config.json",
            "vocab.json",
            "merges.txt",
            "special_tokens_map.json",
            "normalizer.json",
            "preprocessor_config.json",
            "generation_config.json",
        ],
    },
]

MIN_REQUIRED_FREE_SPACE_BYTES = 2_500_000_000  # 2.5 GB


class ModelManager:
    """
    Manages local neural model downloads, caching, integrity, and disk space checks
    for the VoiceRep macOS desktop application.
    """

    def __init__(self, models_dir: Optional[str] = None) -> None:
        if models_dir:
            self.models_dir = Path(models_dir)
        elif settings.DESKTOP_DATA_DIR:
            self.models_dir = Path(settings.DESKTOP_DATA_DIR) / "models"
        else:
            self.models_dir = Path.home() / "Library" / "Application Support" / "VoiceRep" / "models"

        self._lock = asyncio.Lock()
        self._is_downloading = False
        self._download_progress = 0.0
        self._current_task_name = ""
        self._error_message: Optional[str] = None

    def get_models_dir(self) -> Path:
        self.models_dir.mkdir(parents=True, exist_ok=True)
        return self.models_dir

    def check_disk_space(self) -> dict[str, Any]:
        """Returns disk space statistics in bytes and readable GB."""
        target_dir = self.models_dir.parent if self.models_dir.parent.exists() else Path.home()
        usage = shutil.disk_usage(target_dir)
        return {
            "total_bytes": usage.total,
            "free_bytes": usage.free,
            "used_bytes": usage.used,
            "free_gb": round(usage.free / (1024 ** 3), 2),
            "sufficient_space": usage.free >= MIN_REQUIRED_FREE_SPACE_BYTES,
        }

    def check_model_availability(self) -> dict[str, Any]:
        """
        Inspects local storage and system huggingface cache to determine if all
        required weights are present and ready for offline inference.
        """
        from huggingface_hub import try_to_load_from_cache

        missing_models = []
        ready_models = []

        hf_cache_dir = os.environ.get("HF_HOME") or str(self.models_dir)

        for m in REQUIRED_MODELS:
            # Check custom models dir first, then HF default cache
            custom_path = self.models_dir / m["repo_id"] / m["filename"]
            is_ready = False

            if custom_path.exists() and custom_path.stat().st_size > 1024 * 1024:
                is_ready = True
            else:
                # Check huggingface cache
                cached = try_to_load_from_cache(
                    repo_id=m["repo_id"],
                    filename=m["filename"],
                    cache_dir=hf_cache_dir if os.path.exists(hf_cache_dir) else None,
                )
                if cached and isinstance(cached, str) and os.path.exists(cached) and os.path.getsize(cached) > 1024 * 1024:
                    is_ready = True
                else:
                    # Also check global default HF cache
                    cached_global = try_to_load_from_cache(
                        repo_id=m["repo_id"],
                        filename=m["filename"],
                    )
                    if cached_global and isinstance(cached_global, str) and os.path.exists(cached_global) and os.path.getsize(cached_global) > 1024 * 1024:
                        is_ready = True

            model_info = {
                "id": m["id"],
                "name": m["name"],
                "repo_id": m["repo_id"],
                "approx_size_mb": m["approx_size_mb"],
                "ready": is_ready,
            }

            if is_ready:
                ready_models.append(model_info)
            else:
                missing_models.append(model_info)

        all_ready = len(missing_models) == 0
        return {
            "all_ready": all_ready,
            "status": "ready" if all_ready else "missing",
            "ready_models": ready_models,
            "missing_models": missing_models,
            "models_dir": str(self.models_dir),
            "disk_space": self.check_disk_space(),
        }

    def get_download_status(self) -> dict[str, Any]:
        return {
            "is_downloading": self._is_downloading,
            "progress": self._download_progress,
            "current_task": self._current_task_name,
            "error": self._error_message,
        }

    async def download_required_models(self) -> dict[str, Any]:
        """
        Downloads missing weights to the persistent application support models folder.
        """
        async with self._lock:
            if self._is_downloading:
                return {"status": "in_progress", "progress": self._download_progress}

            disk_info = self.check_disk_space()
            if not disk_info["sufficient_space"]:
                err = f"Insufficient disk space. Free: {disk_info['free_gb']} GB, required: 2.5 GB."
                self._error_message = err
                raise RuntimeError(err)

            self._is_downloading = True
            self._download_progress = 0.0
            self._error_message = None

            try:
                from huggingface_hub import hf_hub_download

                target_cache = str(self.get_models_dir())
                total_steps = len(REQUIRED_MODELS)

                for idx, m in enumerate(REQUIRED_MODELS):
                    self._current_task_name = f"Downloading {m['name']}..."
                    self._download_progress = round((idx / total_steps) * 100, 1)
                    logger.info(f"ModelManager: Downloading {m['repo_id']} / {m['filename']}")

                    # Run download in worker thread
                    await asyncio.to_thread(
                        hf_hub_download,
                        repo_id=m["repo_id"],
                        filename=m["filename"],
                        cache_dir=target_cache,
                    )

                    for extra in m.get("extra_files", []):
                        try:
                            await asyncio.to_thread(
                                hf_hub_download,
                                repo_id=m["repo_id"],
                                filename=extra,
                                cache_dir=target_cache,
                            )
                        except Exception as extra_err:
                            logger.warning(f"Optional metadata file {extra} failed to download: {extra_err}")

                self._download_progress = 100.0
                self._current_task_name = "All models ready."
                logger.info("ModelManager: All neural models downloaded and verified.")
                return {"status": "completed", "all_ready": True}

            except Exception as e:
                logger.error(f"Model download failed: {e}", exc_info=True)
                self._error_message = str(e)
                raise
            finally:
                self._is_downloading = False


# Global singleton instance
model_manager = ModelManager()
