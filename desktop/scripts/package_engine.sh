#!/usr/bin/env bash
set -e

# ==============================================================================
# VoiceRep: Standalone Neural Engine Packager
# Packages Python 3.11, PyTorch (MPS/arm64), F5-TTS DiT, Whisper, and FastAPI
# into a self-contained onedir executable for the macOS desktop application.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/Caskroom/miniforge/base/envs/voicerep/bin:/opt/homebrew/bin:$PATH"

echo "=== Packaging VoiceRep Neural Inference Engine (Apple Silicon) ==="

# 1. Clean previous build caches
rm -rf desktop/build desktop/dist

# 2. Run PyInstaller with all required hidden imports and metadata
pyinstaller \
  --name voicerep-engine \
  --onedir \
  --noconfirm \
  --clean \
  --distpath desktop/dist \
  --workpath desktop/build \
  --paths backend \
  --collect-all f5_tts \
  --collect-all x_transformers \
  --collect-all vocos \
  --collect-all transformers \
  --collect-all optree \
  --collect-all soundfile \
  --collect-all librosa \
  --collect-all cached_path \
  --collect-all omegaconf \
  --collect-all hydra \
  --collect-all packaging \
  --collect-all aiosqlite \
  --collect-all uvicorn \
  --hidden-import aiosqlite \
  --hidden-import sqlite3 \
  --hidden-import soundfile \
  --hidden-import packaging \
  --hidden-import packaging.version \
  --hidden-import transformers.pipelines \
  --exclude-module torchcodec \
  --copy-metadata torch \
  --copy-metadata torchaudio \
  --copy-metadata optree \
  --copy-metadata packaging \
  --copy-metadata transformers \
  --copy-metadata huggingface_hub \
  --copy-metadata librosa \
  --copy-metadata vocos \
  --copy-metadata f5_tts \
  --copy-metadata soundfile \
  backend/desktop_entrypoint.py

# 3. Deploy to Tauri resources
mkdir -p desktop/src-tauri/resources/engine
rm -rf desktop/src-tauri/resources/engine/voicerep-engine
cp -R desktop/dist/voicerep-engine desktop/src-tauri/resources/engine/
chmod +x desktop/src-tauri/resources/engine/voicerep-engine/voicerep-engine

# 4. Smoke test
echo "Running engine smoke test..."
./desktop/src-tauri/resources/engine/voicerep-engine/voicerep-engine --help > /dev/null
echo "✓ VoiceRep Standalone Engine packaged and verified successfully."
