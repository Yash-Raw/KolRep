import logging
from fastapi import APIRouter, Depends
import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.database.session import get_db

logger = logging.getLogger("voicerep.health")
router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    db_status = "healthy"
    redis_status = "healthy"

    # Test database
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = f"unhealthy: {str(e)}"

    # Test Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        await r.aclose()
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        redis_status = f"unhealthy: {str(e)}"

    overall = "ok" if db_status == "healthy" and redis_status == "healthy" else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
        "environment": settings.APP_ENV,
        "version": "1.0.0",
    }
