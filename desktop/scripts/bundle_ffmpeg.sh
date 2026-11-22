#!/usr/bin/env bash
set -e

# ==============================================================================
# KolRep: Standalone Apple Silicon FFmpeg Bundler
# Recursively packages ffmpeg, ffprobe, and all Mach-O dylib dependencies
# into desktop/src-tauri/resources/ for self-contained desktop execution.
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
TARGET_DIR="$ROOT_DIR/desktop/src-tauri/resources"
TARGET_BIN="$TARGET_DIR/bin"
TARGET_LIB="$TARGET_DIR/lib"

mkdir -p "$TARGET_BIN" "$TARGET_LIB"

echo "=== Bundling Apple Silicon FFmpeg for KolRep Desktop ==="

# Find source FFmpeg (prefer active conda env, standard kolrep conda env, then PATH)
CONDA_BIN=""
for cand in "${CONDA_PREFIX:+$CONDA_PREFIX/bin}" "$HOME/miniforge3/envs/kolrep/bin" "$HOME/miniconda3/envs/kolrep/bin" "/opt/homebrew/Caskroom/miniforge/base/envs/kolrep/bin"; do
    if [ -n "$cand" ] && [ -x "$cand/ffmpeg" ] && [ -x "$cand/ffprobe" ]; then
        CONDA_BIN="$cand"
        break
    fi
done

if [ -n "$CONDA_BIN" ]; then
    SRC_FFMPEG="$CONDA_BIN/ffmpeg"
    SRC_FFPROBE="$CONDA_BIN/ffprobe"
    SRC_LIB="$(dirname "$CONDA_BIN")/lib"
else
    echo "Locating ffmpeg from PATH..."
    SRC_FFMPEG="$(which ffmpeg)"
    SRC_FFPROBE="$(which ffprobe)"
    SRC_LIB="$(dirname "$(dirname "$SRC_FFMPEG")")/lib"
fi

echo "Copying executables..."
cp -f "$SRC_FFMPEG" "$TARGET_BIN/ffmpeg"
cp -f "$SRC_FFPROBE" "$TARGET_BIN/ffprobe"
chmod +x "$TARGET_BIN/ffmpeg" "$TARGET_BIN/ffprobe"

echo "Resolving and bundling dynamic libraries..."
python3 - << EOF
import os
import subprocess
import shutil
from pathlib import Path

src_lib = Path("$SRC_LIB")
target_lib = Path("$TARGET_LIB")
target_lib.mkdir(parents=True, exist_ok=True)

copied = set()

def resolve_deps(binary_path):
    try:
        out = subprocess.check_output(["otool", "-L", str(binary_path)]).decode("utf-8")
    except Exception:
        return
    for line in out.splitlines()[1:]:
        line = line.strip()
        if not line:
            continue
        dylib_name = line.split()[0]
        if dylib_name.startswith("@rpath/"):
            name = dylib_name[len("@rpath/"):]
            if name not in copied:
                src = src_lib / name
                if src.exists():
                    dst = target_lib / name
                    if not dst.exists():
                        shutil.copy2(src, dst)
                    copied.add(name)
                    resolve_deps(dst)

resolve_deps("$TARGET_BIN/ffmpeg")
resolve_deps("$TARGET_BIN/ffprobe")
print(f"Bundled {len(copied)} dylib dependencies.")
EOF

# Smoke test
echo "Verifying bundled binaries..."
"$TARGET_BIN/ffmpeg" -version | head -n 1
"$TARGET_BIN/ffprobe" -version | head -n 1
echo "✓ Standalone FFmpeg bundling verified successfully."
