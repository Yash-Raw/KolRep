import asyncio
import os
import sys
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.core.security import AuthenticatedUser, get_current_user
from app.database.base import Base
from app.database.session import get_db
from app.main import app
from app.models.user import User

# Use SQLite in-memory for fast unit/integration testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

TEST_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
TEST_USER_EMAIL = "testuser@voicerep.local"

TEST_USER_2_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
TEST_USER_2_EMAIL = "otheruser@voicerep.local"


@pytest_asyncio.fixture
async def setup_test_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session(setup_test_db):
    async with TestingSessionLocal() as session:
        # Pre-seed test users
        u1 = await session.get(User, TEST_USER_ID)
        if not u1:
            session.add(User(id=TEST_USER_ID, email=TEST_USER_EMAIL))
        u2 = await session.get(User, TEST_USER_2_ID)
        if not u2:
            session.add(User(id=TEST_USER_2_ID, email=TEST_USER_2_EMAIL))
        await session.commit()

        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    async def override_get_current_user():
        return AuthenticatedUser(user_id=TEST_USER_ID, email=TEST_USER_EMAIL)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
