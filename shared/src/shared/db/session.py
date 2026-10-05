from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from shared.config import settings


# Single async engine per process. `expire_on_commit=False` keeps ORM objects
# usable after commit (e.g. returning a freshly created payment from a request).
engine = create_async_engine(settings.postgres_dsn_async, pool_pre_ping=True, echo=False)

session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async session, rolling back on error (FastAPI dependency)."""
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
