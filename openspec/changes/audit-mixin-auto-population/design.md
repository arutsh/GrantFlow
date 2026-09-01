## Context

Each of the 4 services (`ai`, `budget`, `chat`, `users`) runs its own independent SQLAlchemy stack — separate `Base` (`app/models/base.py`), separate engine/session factory (`app/db/session.py`), separate database. `ai` and `chat` are async (`create_async_engine`); `budget` and `users` are sync (`create_engine`). There is no shared session layer to hook once.

`get_db` is *not* centralized — it's copy-pasted per route file in `ai`/`budget`, and `chat` doesn't use a `get_db` dependency at all (opens `AsyncSessionLocal()` ad hoc inline in `chat_routes.py`). By contrast, `Depends(get_validated_user)` (from `shared/security/dependencies.py`) *is* used consistently as a `Depends()` across every protected route in all 4 services — this is the one integration point common to every service, so it's where the current-user context should be captured, not `get_db`.

There's already a working precedent for synchronous side-effect code running inside these otherwise-async request paths: `services/ai/app/services/privileged_access_audit.py` runs a dedicated **sync** engine/session for audit-logging purposes from inside `get_validated_user`, with a comment noting it runs synchronously by design. This change follows the same pattern.

## Goals / Non-Goals

**Goals:**
- `created_by` gets set automatically on insert, `updated_by` on insert and update, for any model using `AuditMixin`/`AuditColumnsMixin`, with zero per-CRUD-function code required.
- Works uniformly across sync (`budget`, `users`) and async (`ai`, `chat`) services.
- Fails safe (resolves to `NULL`) on paths with no authenticated request: Celery workers, seed scripts, migrations.
- Single point of registration — not 4 separate wiring jobs — so future services inherit the behavior automatically just by importing the mixin.

**Non-Goals:**
- No schema/migration changes — the columns already exist on the 11 current `AuditMixin` adopters.
- No cross-service FK from `created_by`/`updated_by` to the users table.
- No retroactive backfill of historical NULL values.
- Rolling `AuditMixin` out to more models is out of scope (tracked as separate follow-on changes: `audit-mixin-rollout-tier3`, `audit-mixin-rollout-tier4`).

## Decisions

**1. Capture current-user in `get_validated_user`/`get_current_user`, not in `get_db`.**
`get_db` is duplicated inconsistently and missing entirely in `chat`. `get_validated_user` is the one dependency already used everywhere audit-worthy mutations happen. Alternative considered: a dedicated new `Depends()` per route — rejected, since it would require touching every route file across 4 services instead of one shared function.

**2. Register the SQLAlchemy event listener at import time inside `shared/db/audit_mixin.py` itself, not per-service.**
`event.listens_for(AuditMixin, "before_insert", propagate=True)` (and `AuditColumnsMixin`, and `before_update`) registered as a module-level call in the mixin's own module means any service that imports the mixin gets the behavior automatically — no per-service `main.py` wiring, no risk of a service forgetting to register it. This revises the proposal's "wire into all 4 services" framing to something less error-prone: import-time self-registration in one file.

**3. `ContextVar[uuid.UUID | None]`, set via `.set()` inside the dependency and reset via the returned `Token` in a `finally`.**
Relying purely on Starlette/asyncio per-request context isolation would likely be sufficient, but explicit set/reset is cheap defense-in-depth and makes the lifecycle obvious to a reader. Lives in `shared/security/current_user_context.py` (new module) to avoid overloading `dependencies.py`'s existing responsibility.

**4. `AuditMixin` split: `AuditMixin` (unchanged, `id`-bearing) + new `AuditColumnsMixin` (no PK) sharing the event-listener logic.**
Both get the same `before_insert`/`before_update` hooks registered against a common base so the listener code isn't duplicated.

## Risks / Trade-offs

- **[Risk]** SQLAlchemy's async support runs ORM flush machinery (including mapper events) inside a greenlet via `greenlet_spawn`; contextvar propagation through that boundary is expected to work (this is documented SQLAlchemy asyncio behavior) but hasn't been exercised in this codebase. → **Mitigation**: explicit test in both an async service (`ai` or `chat`) and a sync service (`budget` or `users`) asserting `created_by` is actually populated end-to-end through a real request, not just a unit test of the listener in isolation.
- **[Risk]** Starlette runs sync `Depends()` functions (as in `budget`/`users`) in a thread pool (`anyio.to_thread.run_sync`); contextvars set in the main request task must propagate into that thread. → **Mitigation**: same end-to-end test as above covers this; `anyio.to_thread.run_sync` copies the calling context by default, so this is expected to work, but must be verified rather than assumed.
- **[Risk]** Removing the manual `created_by=`/`updated_by=` assignments in the 8 budget CRUD functions changes behavior if any caller currently passes a `user_id` that differs from the authenticated request's user (e.g., a background/admin-on-behalf-of flow). → **Mitigation**: audit each of the 8 call sites before removing the manual assignment; keep the manual path as an explicit override if any such case exists instead of deleting it outright.
- **[Trade-off]** Centralizing registration inside `shared/db/audit_mixin.py` means the event listener always fires for every model using the mixin — there's no per-model opt-out. Acceptable since the whole point is universal, un-forgettable coverage.

## Migration Plan

No database migration. This is a behavior-only change (how existing columns get populated), so it deploys as a normal code release per service — order doesn't matter across services since each is independent. Rollback is a normal code revert; worst case on rollback is `created_by`/`updated_by` return to their pre-change behavior (manual/absent), not data loss.

## Open Questions

- Should the manual `created_by=`/`updated_by=` CRUD assignments be deleted outright, or left in place as a harmless no-op override, pending the per-call-site audit noted above?
- `before_update` fires whenever SQLAlchemy's unit-of-work marks *any* attribute dirty, including relationship-only changes with no meaningful column update — is that granularity acceptable for `updated_by`, or should it be scoped to specific column changes?
