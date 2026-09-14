"""
Tests for `budget_ledger_lock` (currency_ledger_services.py): the
pg_advisory_lock-based fix for the FIFO allocation race flagged in code
review on ticket #148 — two concurrent requests against the same budget
could both read the same unconsumed-lot balance and double-spend it.

Requires the real local Postgres (docker-compose's `grandflow-db` service)
to be running — skipped automatically otherwise, since advisory locks are
a Postgres-only feature this sqlite-backed test suite can't otherwise
exercise, and session-level locking across two *separate* connections is
the whole point of this design (a mock can't stand in for that).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.services.currency_ledger_services import budget_ledger_lock

pytestmark = pytest.mark.anyio


@pytest.fixture
async def pg_session():
    # NullPool: each connect() is a brand-new physical connection that's
    # fully closed when its `with` block exits — no advisory lock can leak
    # onto a later test via a reused pooled connection.
    db_url = make_url(settings.budget_database_url).set(drivername="postgresql+asyncpg")
    engine = create_async_engine(db_url, poolclass=NullPool)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except OperationalError:
        pytest.skip(f"Postgres not reachable at {settings.budget_database_url}")
    session = async_sessionmaker(engine, expire_on_commit=False)()
    yield session
    await session.close()
    await engine.dispose()


def _lock_key(budget_id) -> int:
    return uuid.UUID(str(budget_id)).int & 0x7FFFFFFFFFFFFFFF


class TestBudgetLedgerLock:
    async def test_blocks_a_second_connection_on_the_same_budget(self, pg_session):
        budget_id = uuid.uuid4()
        key = _lock_key(budget_id)
        probe_engine = AsyncEngine(pg_session.get_bind())

        async with probe_engine.connect() as probe:
            async with budget_ledger_lock(pg_session, budget_id):
                # A second, independent connection trying the same key must
                # fail to acquire it while budget_ledger_lock holds it.
                held = (
                    await probe.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
                ).scalar()
                assert held is False

            # Released once the context manager exits.
            acquired = (
                await probe.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key})
            ).scalar()
            assert acquired is True
            await probe.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})

    async def test_does_not_block_a_different_budget(self, pg_session):
        budget_id_a = uuid.uuid4()
        budget_id_b = uuid.uuid4()
        key_b = _lock_key(budget_id_b)
        probe_engine = AsyncEngine(pg_session.get_bind())

        async with probe_engine.connect() as probe:
            async with budget_ledger_lock(pg_session, budget_id_a):
                held = (
                    await probe.execute(text("SELECT pg_try_advisory_lock(:key)"), {"key": key_b})
                ).scalar()
                assert held is True
                await probe.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key_b})

    async def test_accepts_both_str_and_uuid_budget_id(self, pg_session):
        # GUID (shared/db/type_decorators.py) hands back a plain str on
        # Postgres but a real UUID on sqlite — the lock must key the same
        # regardless of which shape it's given.
        budget_id = uuid.uuid4()

        async with budget_ledger_lock(pg_session, str(budget_id)):
            pass  # no error acquiring/releasing with a str budget_id

        async with budget_ledger_lock(pg_session, budget_id):
            pass  # ...or a uuid.UUID
