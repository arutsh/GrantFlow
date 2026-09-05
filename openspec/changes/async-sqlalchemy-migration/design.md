## Context

`services/budget/app/db/session.py` and `services/users/app/db/session.py` both use `create_engine(SQLALCHEMY_DATABASE_URL)` + `sessionmaker(...)` (psycopg2 driver), with route-level `get_db()` generators yielding a sync `Session`. Every CRUD module (`budget_crud.py`, `budget_line_crud.py`, etc.) uses `.query(Model).filter(...)` and calls `session.commit()`/`session.refresh()` directly inside each function — there is no `commit=False` escape hatch.

`services/ai/app/db/session.py` is the reference: `create_async_engine` with the URL's driver forced to `postgresql+asyncpg` regardless of what's configured in the env file (psycopg2-binary stays only for the Alembic CLI), plus `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`. Its `get_db()` (currently defined locally in `settings_routes.py`) is `async def` and yields the `AsyncSession` directly, no try/finally close needed since `async with` isn't even used there — the session is closed by FastAPI's dependency teardown.

The concrete pain point motivating this now (not just architectural tidiness): `create_budget_with_lines_service` (`services/budget/app/services/budget_services.py:503-566`) creates a budget, then loops creating lines, and on *any* exception — including a mid-loop DB failure — manually deletes every line already created plus the budget itself ("compensating transaction"). This is not atomic: a crash between the last `delete_budget_line` call and `delete_budget` leaves orphaned rows, and it does real extra DB round-trips on every failure path.

Relationship audit (`grep relationship(` across both services) found ~15 relationships in budget's 6 model files, all default lazy-loaded (`lazy="select"`, SQLAlchemy's default), and users has `customer = relationship("CustomerModel", lazy="joined")` (already eager, safe) alongside several default-lazy ones (`sessions`, `users`, `donor`, `grantee`). Every default-lazy relationship accessed outside an already-awaited context will raise `MissingGreenlet` once the session is async.

## Goals / Non-Goals

**Goals:**
- Both services run fully async DB access end-to-end, matching ai-service's pattern exactly (same driver-forcing trick, same `async_sessionmaker` config).
- Zero `MissingGreenlet` risk: every relationship a route/service actually reads is either explicitly eager-loaded (`selectinload`/`joinedload`) at the query site or never accessed lazily.
- `create_budget_with_lines_service` (and any other multi-step writer) uses one real DB transaction — `flush()` inside, single `commit()` at the end — instead of compensating deletes.
- CRUD write functions gain `commit: bool = True`; existing callers are unaffected (default preserves current commit-per-call behavior).

**Non-Goals:**
- No API contract, schema, or request/response shape changes.
- No change to Alembic — migrations keep running sync (psycopg2), same as ai-service.
- Not migrating chat-service (already async from the start) or touching `shared/db/`'s audit mixin behavior beyond what's needed to keep it working under `AsyncSession`.
- Not a performance-tuning pass (connection pool sizing, query optimization) — purely the sync→async mechanical swap plus the atomicity fix already scoped for #59.

## Decisions

**1. Users-service first, then budget-service.** Users has 3 models, budget has 6+ with the with-lines atomicity work layered on top. A clean async dry run on the smaller service surfaces driver/fixture/relationship issues cheaply before the harder service.

**2. Reuse ai-service's exact session-setup pattern, don't invent a new one.** `make_url(...).set(drivername="postgresql+asyncpg")` plus `async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)`. Rationale: it's already proven in this repo, keeps all four services' persistence layer consistent, and `expire_on_commit=False` avoids a second class of lazy-load-after-commit surprises (attribute access after `commit()` would otherwise trigger a refresh query).

**3. Centralize `get_db()` per service instead of leaving it duplicated per route file.** Budget currently defines `get_db()` locally in `budget_routes.py`; it's duplicated implicitly if other route files construct their own `Session()`. Move to one `get_db()` in each service's `app/db/session.py` (matching users-service's existing pattern, which already centralizes it) — mechanical cleanup that falls out of touching every route file's import anyway.

**4. Eager-load audit is per-callsite, not "make everything eager by default."** Rather than blanket-setting `lazy="selectin"` on every relationship (which would over-fetch on paths that never touch the relationship), each route/service function that currently accesses a relationship attribute gets an explicit `selectinload()`/`joinedload()` added to its query. This keeps the fetch shape matching actual usage, same discipline the codebase already applies (`users.customer` is already `lazy="joined"` because it's read on nearly every request).

**5. `commit=False` is additive, not a rewrite of CRUD signatures.** Every CRUD write function keeps its current default behavior (`commit=True` → commits immediately, unchanged for 100% of existing callers) and gains one new optional kwarg. Only `create_budget_with_lines_service` (and its inner calls to `create_budget_service`/`create_budget_line_service`) is rewired to pass `commit=False` and drive one shared `db.commit()` at the end — no other caller needs to change.

**6. Alternative considered and rejected: migrate both services simultaneously in one PR.** Rejected — larger blast radius, harder to bisect a regression to "the async swap" vs. "the atomicity change," and the proposal's own ordering (users first as a dry run) only pays off if it lands and is validated before budget starts.

**7. Convert `AuditMixin`'s `created_at`/`updated_at` from DB-side to Python-side defaults, as a prerequisite of this migration.** `shared/db/audit_mixin.py` currently computes both columns via `default=func.now()`/`onupdate=func.now()` — values that only exist once the DB executes the INSERT/UPDATE, which is exactly why `create_budget_category`/`update_budget_category` call `session.refresh()` today to get them back. `services/ai`'s models never needed that: their timestamps are set in Python (`datetime.now(timezone.utc)`) before the commit, which is only safe under `expire_on_commit=False` (Decision 2) because there's no DB-computed value left to miss. Adopting Decision 2 without this change means any commit path that reads these attributes without an explicit refresh — the budget-service's `bulk_create_budget_categories` was one such case, found and fixed 2026-09-05 — silently returns stale/`None` timestamps instead of raising. Fixing the mixin itself (once) is cheaper than auditing every commit site across the ~11 models that have it today plus the 17 pending the audit-mixin-rollout changes. This edit is scoped to *this* change, not `audit-mixin-rollout-tier3`/`tier4`/`auto-population`/`coverage-guard`, since those changes are about which models carry the mixin and how its adoption is enforced, not how its own columns compute their values.

## Risks / Trade-offs

- [Missed lazy-load site slips through review, surfaces as a runtime `MissingGreenlet` in an untested code path] → Mitigation: run the full existing test suite (converted to async fixtures) plus a manual smoke pass through every route in both services before merging each service's migration.
- [`expire_on_commit=False` masks a stale-attribute bug if code assumes post-commit attributes reflect DB-computed defaults (e.g. server-side timestamps)] → Confirmed real, not hypothetical: `AuditMixin.created_at`/`updated_at` are exactly such DB-computed defaults. Resolved by Decision 7 (convert the mixin to Python-side timestamps before either service flips `expire_on_commit`) instead of auditing every commit site for a missing refresh.
- [Test infra: budget/users tests currently use sync fixtures/sessions; switching to async requires new fixtures, following `services/ai/tests`' existing async pattern (already validated in this repo) rather than inventing one] → Mitigation covered by reusing that pattern directly.
- [Threadpool removal changes concurrency characteristics under load — theoretically better, but unverified under this repo's actual traffic shape] → Accepted; no production traffic exists yet to validate against, and this is explicitly the cheapest time to take that risk (see proposal's "Why now").

## Migration Plan

0. `AuditMixin` timestamp defaults: convert `created_at`/`updated_at` to Python-side values in `shared/db/audit_mixin.py`, confirm via the existing sync test suites (no async work yet) that nothing changes behaviorally, before either service touches its session config.
1. Users-service: swap session/engine, centralize `get_db()`, convert `app/crud/*.py` to `select()`-style async, add `selectinload`/`joinedload` at each relationship-accessing callsite, convert test fixtures to async, full test pass + manual smoke test.
2. Budget-service: same mechanical steps across its larger CRUD/route surface.
3. Budget-service, layered on top of step 2: add `commit: bool = True` to CRUD write functions, rewire `create_budget_with_lines_service` to `flush()`-then-single-`commit()`, delete the compensating-transaction delete calls.
4. Each service ships as its own PR/ticket chain (per this repo's one-chunk-one-ticket-one-PR workflow) — no shared PR.

**Rollback:** each service's migration is independently revertable (git revert the service's PR) since neither touches the other service, the API contract, or the DB schema — no data migration to unwind.

## Open Questions

- Whether Alembic's `env.py` in each service needs any change given the driver-forcing happens in `db/session.py`, not the URL in `alembic.ini` — likely no, since ai-service's Alembic already runs sync against the same psycopg2 URL unmodified, but worth confirming per-service during implementation.
