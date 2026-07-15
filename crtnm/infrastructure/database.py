"""SQLAlchemy session lifecycle."""
from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from crtnm.core.config import get_settings


class Base(DeclarativeBase):
    """Base class for ORM entities."""


engine = create_engine(get_settings().database_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    """Yield a transaction-scoped database session."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

