#!/usr/bin/env bash
set -e

# ==============================================================================
# VoiceRep: Turnkey Local Startup Script
# Boots full-stack VoiceRep: Postgres, Redis, Alembic, FastAPI backend, Next.js
# ==============================================================================

echo "========================================================"
echo "  🚀 Starting VoiceRep Full-Stack Local Platform        "
echo "========================================================"

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

# 1. Environment & Python Resolution
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$PATH"
CONDA_VOICEREP="/opt/homebrew/Caskroom/miniforge/base/envs/voicerep/bin"
if [ -d "$CONDA_VOICEREP" ]; then
    export PATH="$CONDA_VOICEREP:$PATH"
fi

PYTHON_CMD="python3"
if command -v python &> /dev/null; then
    PYTHON_CMD="python"
fi

PY_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || echo "0.0")
echo "✓ Python detected: $PYTHON_CMD (v$PY_VERSION)"

# 2. Check FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✓ FFmpeg binary found: $(which ffmpeg)"
else
    echo "⚠️  FFmpeg not found in PATH. Please install ffmpeg for audio processing."
fi

# 3. Check / Start PostgreSQL & Redis services
echo "Checking database and cache services..."
if command -v pg_isready &> /dev/null && pg_isready -q; then
    echo "✓ PostgreSQL is active and ready."
elif docker ps --format '{{.Names}}' | grep -q 'voicerep_postgres'; then
    echo "✓ PostgreSQL container is running."
else
    echo "Starting PostgreSQL and Redis via Docker Compose..."
    docker compose up -d db redis 2>/dev/null || docker-compose up -d db redis 2>/dev/null || echo "Note: Starting background services (ensure DB is running on :5432)."
fi

# 4. Apply Alembic Migrations
echo "Applying latest database migrations..."
(cd backend && alembic upgrade head)
echo "✓ Database schema verified and up to date."

# 5. Trap signals for graceful shutdown
cleanup() {
    echo ""
    echo "Shutting down VoiceRep services..."
    kill $(jobs -p) 2>/dev/null || true
    echo "VoiceRep stopped safely."
    exit 0
}
trap cleanup SIGINT SIGTERM EXIT

# 6. Boot FastAPI Backend (Port 8000)
echo "Starting VoiceRep FastAPI Backend on http://localhost:8000 ..."
(cd backend && $PYTHON_CMD -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload) &
BACKEND_PID=$!

# 7. Boot Next.js Frontend (Port 3000)
echo "Starting VoiceRep Next.js Frontend on http://localhost:3000 ..."
(cd frontend && npm run dev) &
FRONTEND_PID=$!

echo ""
echo "========================================================"
echo "  🎉 VoiceRep is running live!                          "
echo "  • Frontend Web Studio:  http://localhost:3000        "
echo "  • Backend API & Docs:   http://localhost:8000/docs   "
echo "  • Health Endpoint:      http://localhost:8000/api/v1/health"
echo "========================================================"
echo "Press Ctrl+C to stop all services."
echo ""

wait
