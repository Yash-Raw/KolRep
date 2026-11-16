import asyncio
from contextlib import asynccontextmanager
import glob
import logging
import os
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api.v1 import api_v1_router
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("voicerep.app")


def clean_stale_temp_files() -> None:
    """Safely cleans up orphaned temporary generation chunks and uploads."""
    try:
        # 1. Clean up temp files inside voice profiles dir
        voice_dir = Path(settings.SELF_HOSTED_VOICE_DIR)
        if voice_dir.exists():
            for p in voice_dir.glob("**/temp_*"):
                try:
                    if p.is_file():
                        p.unlink(missing_ok=True)
                except Exception:
                    pass

        # 2. Clean up /tmp upload temp files
        for p_str in glob.glob("/tmp/upload_*"):
            try:
                os.remove(p_str)
            except Exception:
                pass
    except Exception as e:
        logger.warning(f"Error cleaning stale temporary files: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting VoiceRep API server...")
    clean_stale_temp_files()

    # Initialize SQLite database schema automatically when running in desktop mode
    if settings.VOICEREP_DESKTOP_MODE:
        try:
            from app.database.session import init_db
            await init_db()
            logger.info("Desktop SQLite database initialized successfully.")
        except Exception as e:
            logger.error(f"Desktop database initialization failed: {e}")

    # Pre-warm self-hosted engines in the background if configured
    if settings.VOICE_PROVIDER == "self_hosted":
        async def _prewarm():
            try:
                if settings.VOICEREP_DESKTOP_MODE:
                    from app.desktop.model_manager import model_manager
                    if not model_manager.check_model_availability()["all_ready"]:
                        logger.info("Desktop mode: Neural models not yet downloaded; skipping pre-warming until first-run setup.")
                        return

                from app.providers.self_hosted import self_hosted_provider
                logger.info("Pre-warming Self-Hosted F5-TTS and Whisper engines...")
                await self_hosted_provider.get_engine()
                await self_hosted_provider.get_asr_pipeline()
                logger.info("Self-Hosted neural engines pre-warmed successfully.")
            except Exception as e:
                logger.warning(f"Engine pre-warming skipped or deferred: {e}")

        asyncio.create_task(_prewarm())

    yield

    logger.info("Shutting down VoiceRep API server...")
    clean_stale_temp_files()


app = FastAPI(
    title="VoiceRep API",
    description="100% Local AI Voice Replication & Studio Narration Platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Configuration
origins = [
    settings.FRONTEND_URL,
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1)(:[0-9]+)?|tauri://.*|https?://tauri\.localhost.*|asset://.*)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled server error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


# Mount API routers
app.include_router(api_v1_router)


@app.get("/")
async def root():
    return {
        "service": "VoiceRep API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
