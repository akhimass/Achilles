"""Async SQLAlchemy engine and session dependency.

The schema itself lives in `db/schema.sql` (loaded by Postgres on init) — this
module is the runtime connection, not a source of truth for table definitions.
Phase 1+ can add SQLAlchemy table mappings here if ORM access is preferred over
raw SQL; until then, use `session.execute(text(...))`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async session."""
    async with SessionLocal() as session:
        yield session
