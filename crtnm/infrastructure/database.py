"""SQLAlchemy session lifecycle."""
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from crtnm.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for ORM entities."""


settings = get_settings()
database_url = settings.database_url

# Check if using SQLite
is_sqlite = database_url.startswith("sqlite")

if is_sqlite:
    # SQLite doesn't support async properly, use sync only
    engine = create_engine(database_url, future=True, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    AsyncSessionLocal = None
else:
    # PostgreSQL - use both sync and async
    engine = create_engine(database_url, future=True)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    
    # Convert PostgreSQL URL for async
    async_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    async_engine = create_async_engine(async_url, future=True)
    AsyncSessionLocal = async_sessionmaker(bind=async_engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_session() -> Generator[Session, None, None]:
    """Yield a transaction-scoped database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


async def get_async_session() -> Generator[AsyncSession, None, None]:
    """Yield an async database session."""
    if AsyncSessionLocal is None:
        raise RuntimeError("Async sessions not supported with SQLite. Use PostgreSQL for async operations.")
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

