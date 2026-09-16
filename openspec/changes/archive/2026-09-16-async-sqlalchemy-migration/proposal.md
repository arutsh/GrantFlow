## Why

`services/budget` and `services/users` still use sync SQLAlchemy (`create_engine`/`SessionLocal`/psycopg2) injected into `async def` FastAPI endpoints; `services/ai` already runs fully async (`create_async_engine`/asyncpg). FastAPI silently threadpools the sync calls, which works today but creates architectural inconsistency and thread-pool pressure under load. There's no production database yet — this is the cheapest point in the project's life to fix it, using the ai-service migration as the reference implementation. Bundled in: the CRUD layer's `commit=False`/`session.flush()` support (GitHub #59), deferred from the `/budgets/with-lines` endpoint, whose current compensating-transaction workaround (deleting already-committed rows on partial failure) this migration is the natural point to replace with real transactional atomicity.

## What Changes

- Both services: `create_engine` → `create_async_engine` (asyncpg driver), `SessionLocal` → `async_sessionmaker`/`AsyncSession`, `db: Session = Depends(get_db)` → `db: AsyncSession = Depends(get_db)`.
- All CRUD `.query()` calls → `select()`-style async queries (`await db.execute(...)`, `await db.commit()`).
- Pre-work: audit every lazily-loaded relationship in both services' models and convert to explicit `selectinload`/`joinedload`, since lazy loading raises `MissingGreenlet` under an async session.
- CRUD write functions gain an optional `commit: bool = True` parameter; `commit=False` calls `session.flush()` instead of `session.commit()`, letting multi-step callers (e.g. `create_budget_with_lines_service`) manage one real transaction instead of compensating deletes.
- **BREAKING**: internal only — every route/service function that depends on `Session`/`SessionLocal` in these two services changes signature to `AsyncSession`. No external API contract changes.
- Order: users-service first (smaller surface, dry run), then budget-service (larger surface, including the with-lines atomic-write path).

## Capabilities

### New Capabilities
- `async-persistence`: the architectural requirement that budget-service and users-service perform all database access asynchronously end-to-end (async engine, async session, non-blocking queries), with no lazy-loaded relationships that could raise `MissingGreenlet`, and that multi-step writes use real DB-level transactions (`flush`-then-`commit`) rather than compensating transactions.

### Modified Capabilities
- None — no product-facing request/response contract changes; existing capability specs describe behavior, not persistence implementation.

## Impact

- Code: `services/budget/app/**` and `services/users/app/**` — engine/session setup, all CRUD modules, all route handlers, all service-layer functions with DB calls, model relationship definitions.
- Tests: both services' test suites need async fixtures (see `services/ai/tests` for the existing pattern) and DB-session mocking updates.
- Dependencies: both services need `asyncpg` added; psycopg2 can be dropped once Alembic (which can stay sync) no longer needs it, or kept solely for Alembic migrations if simpler.
- No schema changes, no API contract changes, no infra/deploy changes.
