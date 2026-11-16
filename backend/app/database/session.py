from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

# Engine configuration
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # Ensure database directory exists if file-backed SQLite
    clean_path = settings.DATABASE_URL.split("sqlite:///")[-1].split("sqlite+aiosqlite:///")[-1]
    if clean_path and not clean_path.startswith(":memory:"):
        from pathlib import Path
        Path(clean_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,
    connect_args=connect_args
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def init_db() -> None:
    """Initialize database tables and seed default user for local desktop operation."""
    from sqlalchemy import select
    from app.database.base import Base
    from app.models.user import User
    from app.core.security import DEFAULT_LOCAL_USER_ID, DEFAULT_LOCAL_USER_EMAIL

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == DEFAULT_LOCAL_USER_ID)
        res = await session.execute(stmt)
        if not res.scalar_one_or_none():
            session.add(User(id=DEFAULT_LOCAL_USER_ID, email=DEFAULT_LOCAL_USER_EMAIL))
            await session.commit()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
