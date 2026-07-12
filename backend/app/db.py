"""Async SQLAlchemy engine and session dependency.

The schema itself lives in `db/schema.sql` (loaded by Postgres on init) — this
module is the runtime connection, not a source of truth for table definitions.
Phase 1+ can add SQLAlchemy table mappings here if ORM access is preferred over
raw SQL; until then, use `session.execute(text(...))`.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.config import settings

# When running against a transaction-mode connection pooler (Supabase/pgbouncer on
# :6543), asyncpg's default numeric prepared-statement names collide across the
# server connections the pooler multiplexes, raising DuplicatePreparedStatementError.
# The documented fix: give every prepared statement a unique name and stop caching
# them, and let the server-side pooler own pooling (NullPool). Local/direct Postgres
# (the default URL) is unaffected — it keeps the normal connection pool.
_is_pooled_asyncpg = settings.database_url.startswith("postgresql+asyncpg")
_engine_kwargs: dict = {"pool_pre_ping": True}
if _is_pooled_asyncpg:
    _engine_kwargs["poolclass"] = NullPool
    _engine_kwargs["connect_args"] = {
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4()}__",
    }

engine = create_async_engine(settings.database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding an async session."""
    async with SessionLocal() as session:
        yield session
