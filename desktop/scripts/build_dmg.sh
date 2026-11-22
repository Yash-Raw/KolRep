#!/usr/bin/env bash
set -e

# ==============================================================================
# KolRep: Turnkey macOS DMG Packaging Pipeline (Apple Silicon arm64)
# Builds static frontend, bundles FFmpeg & dynamic libraries, packages the
# standalone neural engine, compiles Tauri app, and produces KolRep.dmg.
# ==============================================================================

echo "========================================================"
echo "  📦 Building KolRep Native macOS DMG Installer         "
echo "  Target: macOS (Apple Silicon arm64)                   "
echo "========================================================"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$ROOT_DIR"

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$HOME/.cargo/bin:$PATH"
for cand in "${CONDA_PREFIX:+$CONDA_PREFIX/bin}" "$HOME/miniforge3/envs/kolrep/bin" "$HOME/miniconda3/envs/kolrep/bin" "/opt/homebrew/Caskroom/miniforge/base/envs/kolrep/bin"; do
    if [ -n "$cand" ] && [ -d "$cand" ]; then
        export PATH="$cand:$PATH"
        break
    fi
done
export CI=true
export NEXT_TELEMETRY_DISABLED=1

# 1. Build Next.js Static Export
echo ""
echo "--- Step 1/4: Exporting Next.js Studio Frontend ---"
(cd frontend && npm run export)
echo "✓ Frontend statically exported to frontend/out."

# 2. Bundle Standalone Apple Silicon FFmpeg
echo ""
echo "--- Step 2/4: Bundling Standalone FFmpeg & Codecs ---"
"$ROOT_DIR/desktop/scripts/bundle_ffmpeg.sh"

# 3. Ensure Standalone Neural Engine is Packaged
echo ""
echo "--- Step 3/4: Verifying Packaged Neural Inference Engine ---"
ENGINE_BIN="$ROOT_DIR/desktop/src-tauri/resources/engine/kolrep-engine/kolrep-engine"
if [ ! -f "$ENGINE_BIN" ] || [ "${REBUILD_ENGINE:-0}" = "1" ] || [ "$1" = "--rebuild-engine" ]; then
    echo "Packaging standalone neural engine with PyInstaller..."
    "$ROOT_DIR/desktop/scripts/package_engine.sh"
else
    echo "✓ Existing packaged neural engine verified at:"
    echo "  $ENGINE_BIN"
fi

# 4. Compile Tauri App Bundle & Package DMG
echo ""
echo "--- Step 4/4: Compiling Native Tauri Shell & Building DMG ---"
cd "$ROOT_DIR/desktop"

# Compile application bundle
npx --yes @tauri-apps/cli build --target aarch64-apple-darwin

APP_PATH="$(find "$ROOT_DIR/desktop/src-tauri/target" -name "KolRep.app" | grep -v "build" | head -n 1)"
if [ -z "$APP_PATH" ] || [ ! -d "$APP_PATH" ]; then
    echo "❌ Error: KolRep.app was not generated."
    exit 1
fi

DMG_DIR="$ROOT_DIR/desktop/src-tauri/target/aarch64-apple-darwin/release/bundle/dmg"
mkdir -p "$DMG_DIR"
DMG_PATH="$DMG_DIR/KolRep_1.0.0_aarch64.dmg"

echo "Creating compressed Apple Silicon DMG with /Applications shortcut..."
TMP_DMG_DIR="$(mktemp -d)"
cp -R "$APP_PATH" "$TMP_DMG_DIR/"
ln -s /Applications "$TMP_DMG_DIR/Applications"

hdiutil create -volname "KolRep" -srcfolder "$TMP_DMG_DIR" -ov -format UDZO "$DMG_PATH"
rm -rf "$TMP_DMG_DIR"

echo ""
echo "========================================================"
echo "  🎉 KolRep macOS Application & DMG Build Complete!     "
echo "========================================================"
DMG_SIZE="$(du -h "$DMG_PATH" | cut -f1)"
APP_SIZE="$(du -h -d 0 "$APP_PATH" | cut -f1)"
echo "  • Output DMG:  $DMG_PATH ($DMG_SIZE)"
echo "  • Output App:  $APP_PATH ($APP_SIZE)"
echo "========================================================"
