import os
import tempfile
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from app.core.config import Settings
from app.core.security import DEFAULT_LOCAL_USER_ID
from app.database.session import AsyncSessionLocal, init_db
from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_desktop_settings_resolution():
    with tempfile.TemporaryDirectory() as tmpdir:
        s = Settings(
            KOLREP_DESKTOP_MODE=True,
            DESKTOP_DATA_DIR=tmpdir,
        )
        assert s.KOLREP_DESKTOP_MODE is True
        assert s.ENABLE_REDIS is False
        assert s.DATABASE_URL.startswith("sqlite+aiosqlite:///")
        assert tmpdir in s.DATABASE_URL
        assert tmpdir in s.LOCAL_STORAGE_PATH
        assert tmpdir in s.SELF_HOSTED_VOICE_DIR


@pytest.mark.asyncio
async def test_desktop_init_db():
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = os.path.join(tmpdir, "database", "test.db")
        # Initialize tables
        await init_db()

        # Check default user exists in session
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.id == DEFAULT_LOCAL_USER_ID)
            res = await session.execute(stmt)
            user = res.scalar_one_or_none()
            assert user is not None
            assert user.id == DEFAULT_LOCAL_USER_ID


@pytest.mark.asyncio
async def test_desktop_health_endpoint(client):
    from app.core.config import settings
    original_desktop = settings.KOLREP_DESKTOP_MODE
    original_redis = settings.ENABLE_REDIS
    try:
        settings.KOLREP_DESKTOP_MODE = True
        settings.ENABLE_REDIS = False

        res = await client.get("/api/v1/health")
        assert res.status_code == 200
        data = res.json()
        assert data["desktop_mode"] is True
        assert "disabled" in data["redis"]
        assert data["status"] == "ok"
    finally:
        settings.KOLREP_DESKTOP_MODE = original_desktop
        settings.ENABLE_REDIS = original_redis


@pytest.mark.asyncio
async def test_desktop_status_endpoint(client):
    res = await client.get("/api/v1/desktop/status")
    assert res.status_code == 200
    data = res.json()
    assert "platform" in data
    assert "arch" in data
    assert "device" in data
    assert "models" in data
    assert "ffmpeg" in data


@pytest.mark.asyncio
async def test_local_job_manager():
    import asyncio
    from app.desktop.job_manager import local_job_manager

    async def sample_task(job_id, delay=0.05):
        await asyncio.sleep(delay)
        return {"result": "success"}

    job_id = "test-job-123"
    job = local_job_manager.submit_job(job_id, "test_synth", sample_task, 0.05)
    assert job.id == job_id
    assert job.status in ("queued", "processing")

    await asyncio.sleep(0.1)
    retrieved = local_job_manager.get_job(job_id)
    assert retrieved is not None
    assert retrieved.status == "completed"
    assert retrieved.result == {"result": "success"}
    assert retrieved.progress == 100.0


@pytest.mark.asyncio
async def test_local_job_cancellation():
    import asyncio
    from app.desktop.job_manager import local_job_manager

    async def long_task(job_id):
        await asyncio.sleep(10.0)
        return {"result": "should not reach"}

    job_id = "test-job-cancel"
    job = local_job_manager.submit_job(job_id, "test_cancel", long_task)
    await asyncio.sleep(0.01)
    cancelled = await local_job_manager.cancel_job(job_id)
    assert cancelled is True
    retrieved = local_job_manager.get_job(job_id)
    assert retrieved.status == "cancelled"

