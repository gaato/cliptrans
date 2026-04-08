"""SQLAlchemy async engine and session factory."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from cliptrans.adapters.persistence.tables import Base

_engines: dict[str, AsyncEngine] = {}
_session_factories: dict[str, async_sessionmaker[AsyncSession]] = {}


def get_engine(database_url: str) -> AsyncEngine:
    engine = _engines.get(database_url)
    if engine is None:
        engine = create_async_engine(
            database_url,
            echo=False,
            future=True,
        )
        _engines[database_url] = engine
    return engine


def get_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    factory = _session_factories.get(database_url)
    if factory is None:
        engine = get_engine(database_url)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        _session_factories[database_url] = factory
    return factory


async def create_tables(database_url: str) -> None:
    """Create all tables (idempotent — uses CREATE IF NOT EXISTS).

    Also ensures the parent directory of a SQLite file exists.
    """
    _ensure_db_dir(database_url)
    engine = get_engine(database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def _ensure_db_dir(database_url: str) -> None:
    """Create the parent directory for a SQLite database URL if needed."""
    # sqlite+aiosqlite:///relative/path/db.sqlite3
    # sqlite+aiosqlite:////absolute/path/db.sqlite3
    if "sqlite" not in database_url:
        return
    parsed = urlparse(database_url)
    # path is the part after the scheme, e.g. "/data/db.sqlite3" or "//data/db.sqlite3"
    db_path_str = parsed.path.lstrip("/")
    if not db_path_str:
        return  # in-memory
    db_path = Path(db_path_str)
    db_path.parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def session_scope(database_url: str) -> AsyncGenerator[AsyncSession]:
    factory = get_session_factory(database_url)
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
