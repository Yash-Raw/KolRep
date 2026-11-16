#!/usr/bin/env python3
"""
VoiceRep Standalone Desktop Backend Entrypoint.
Boots the packaged FastAPI neural inference engine in 100% offline desktop mode.
"""
import argparse
import importlib.metadata
import os
from pathlib import Path
import signal
import sys

# Block torchcodec early to prevent broken native image extension from crashing speech pipeline
sys.modules["torchcodec"] = None
sys.modules["torchcodec.decoders"] = None

# Ensure FFmpeg directory and common binary paths are on os.environ["PATH"] early
_candidate_ffmpeg_paths = [
    os.environ.get("VOICEREP_FFMPEG_PATH"),
    "/opt/homebrew/Caskroom/miniforge/base/envs/voicerep/bin/ffmpeg",
    "/opt/homebrew/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
]
if hasattr(sys, "executable"):
    _exec_dir = Path(sys.executable).resolve().parent
    _candidate_ffmpeg_paths.extend([
        str(_exec_dir / "bin" / "ffmpeg"),
        str(_exec_dir / "ffmpeg"),
        str(_exec_dir.parent / "Resources" / "resources" / "bin" / "ffmpeg"),
        str(_exec_dir.parent / "Resources" / "bin" / "ffmpeg"),
    ])

_ffmpeg_bin = None
for _p in _candidate_ffmpeg_paths:
    if _p and os.path.exists(_p) and os.access(_p, os.X_OK):
        _ffmpeg_bin = _p
        break

if not _ffmpeg_bin:
    import shutil
    _ffmpeg_bin = shutil.which("ffmpeg")

_extra_paths = [
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    "/usr/local/bin",
    "/opt/homebrew/Caskroom/miniforge/base/envs/voicerep/bin",
]
if _ffmpeg_bin:
    _ffmpeg_dir = str(Path(_ffmpeg_bin).resolve().parent)
    if _ffmpeg_dir not in _extra_paths:
        _extra_paths.insert(0, _ffmpeg_dir)
    os.environ["VOICEREP_FFMPEG_PATH"] = _ffmpeg_bin

_current_path = os.environ.get("PATH", "")
_new_path_items = [p for p in _extra_paths if p not in _current_path.split(":")]
if _new_path_items:
    os.environ["PATH"] = f"{':'.join(_new_path_items)}:{_current_path}"

# Patch importlib.metadata.version to prevent PackageNotFoundError inside PyInstaller frozen bundle
_orig_metadata_version = importlib.metadata.version
def _safe_metadata_version(pkg: str) -> str:
    try:
        return _orig_metadata_version(pkg)
    except importlib.metadata.PackageNotFoundError:
        known_defaults = {
            "torchcodec": "0.17.0",
            "transformers": "4.49.0",
            "torch": "2.15.0",
            "torchaudio": "2.15.0",
            "f5_tts": "0.1.0",
            "vocos": "0.1.0",
            "packaging": "26.3",
        }
        return known_defaults.get(pkg, "1.0.0")
importlib.metadata.version = _safe_metadata_version

# Patch torch.jit.script to safely fall back to plain Python function if source code is stripped in frozen bundle
try:
    import torch.jit
    _orig_jit_script = torch.jit.script
    def _safe_jit_script(obj, *args, **kwargs):
        try:
            return _orig_jit_script(obj, *args, **kwargs)
        except Exception:
            return obj
    torch.jit.script = _safe_jit_script
except Exception:
    pass

# Patch torchaudio.load and torchaudio.save with soundfile fallback to prevent torchcodec missing errors
try:
    import soundfile as sf
    import torch
    import torchaudio

    _orig_ta_load = torchaudio.load
    def _safe_ta_load(filepath, *args, **kwargs):
        try:
            return _orig_ta_load(filepath, *args, **kwargs)
        except Exception:
            data, sr = sf.read(str(filepath), dtype="float32")
            tensor = torch.from_numpy(data)
            if tensor.ndim == 1:
                tensor = tensor.unsqueeze(0)
            else:
                tensor = tensor.t()
            return tensor, sr

    _orig_ta_save = torchaudio.save
    def _safe_ta_save(filepath, src, sample_rate, *args, **kwargs):
        try:
            return _orig_ta_save(filepath, src, sample_rate, *args, **kwargs)
        except Exception:
            data = src.detach().cpu().numpy()
            if data.ndim == 2:
                data = data.T
            sf.write(str(filepath), data, sample_rate)

    torchaudio.load = _safe_ta_load
    torchaudio.save = _safe_ta_save
    if hasattr(torchaudio, "load_with_torchcodec"):
        torchaudio.load_with_torchcodec = _safe_ta_load
    if hasattr(torchaudio, "save_with_torchcodec"):
        torchaudio.save_with_torchcodec = _safe_ta_save

    try:
        import torchaudio._torchcodec
        torchaudio._torchcodec.load_with_torchcodec = _safe_ta_load
        torchaudio._torchcodec.save_with_torchcodec = _safe_ta_save
    except Exception:
        pass
except Exception:
    pass

# Ensure transformers.pipeline is safely importable before any dependencies load
try:
    import optree
except Exception:
    pass

# Prevent torchcodec image loader failure inside PyInstaller frozen bundle
try:
    import transformers.utils.import_utils as _hf_import_utils
    _hf_import_utils.is_torchcodec_available = lambda: False
except Exception:
    pass

try:
    import torchcodec._internally_replaced_utils as _tc_utils
    _tc_utils.load_image_library = lambda: None
except Exception:
    pass

try:
    import transformers
    from transformers import pipeline
except Exception as _e:
    import transformers
    def _dummy_pipeline(*args, **kwargs):
        raise NotImplementedError(f"Transformers pipeline fallback: {_e}")
    transformers.pipeline = _dummy_pipeline

# Force PyInstaller to detect and bundle all neural inference and audio dependencies
import aiosqlite
import cached_path
import f5_tts
import f5_tts.api
import f5_tts.infer.utils_infer
import hydra
import librosa
import numpy
import omegaconf
import packaging
import packaging.version
import pydub
import soundfile
import torch
import torchaudio
import uvicorn
import vocos

# Ensure backend root is in sys.path
CURRENT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(CURRENT_DIR))


def main():
    parser = argparse.ArgumentParser(description="VoiceRep Desktop Engine")
    parser.add_argument("--host", default="127.0.0.1", help="Binding host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Binding port (default: 8000)")
    parser.add_argument("--data-dir", default=None, help="Custom data directory")
    args = parser.parse_args()

    # Enable Desktop Mode
    os.environ["VOICEREP_DESKTOP_MODE"] = "1"
    os.environ["ENABLE_REDIS"] = "false"

    base_data_dir = (
        Path(args.data_dir)
        if args.data_dir
        else Path.home() / "Library" / "Application Support" / "VoiceRep"
    )
    base_data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["DESKTOP_DATA_DIR"] = str(base_data_dir)

    # Change working directory to persistent data dir so relative paths never hit macOS root /
    try:
        os.chdir(str(base_data_dir))
    except Exception as e:
        print(f"[VoiceRep Desktop Engine] Warning: could not chdir to {base_data_dir}: {e}", file=sys.stderr)

    # Point HuggingFace home and torch cache to the persistent models directory
    models_dir = base_data_dir / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(models_dir)
    os.environ["TORCH_HOME"] = str(models_dir)

    # Set up persistent file logging to Library/Application Support/VoiceRep/engine.log
    import logging
    engine_log_file = base_data_dir / "engine.log"
    file_handler = logging.FileHandler(str(engine_log_file), encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    logging.getLogger().addHandler(file_handler)
    logging.getLogger("voicerep").addHandler(file_handler)

    # Import app after environment variables are set
    from app.core.config import settings
    from app.desktop.job_manager import local_job_manager
    from app.main import app

    def handle_shutdown(signum, frame):
        import asyncio
        print(f"\n[VoiceRep Desktop Engine] Received termination signal ({signum}). Shutting down...")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(local_job_manager.shutdown())
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    print(f"[VoiceRep Desktop Engine] Starting on http://{args.host}:{args.port}", flush=True)
    print(f"[VoiceRep Desktop Engine] Persistent Data Directory: {base_data_dir}", flush=True)
    print(f"[VoiceRep Desktop Engine] Database URL: {settings.DATABASE_URL}", flush=True)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
