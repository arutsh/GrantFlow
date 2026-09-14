## Context

`shared/security/dependencies.py:get_validated_user` is a synchronous FastAPI dependency, used via `Depends(get_validated_user)` in every route that needs auth across all 4 services. Near the end of that function it calls `log_privileged_access(payload, request)` (`shared/security/privileged_access.py`), which writes an audit row through a registered `_sink` callable whenever the request runs under an impersonation session.

Each service registers its own sink at import time via `make_privileged_access_sink(session_factory, model_cls)`, built on a *synchronous* `session_factory`. All 4 services' primary DB access is already async (`create_async_engine`/`AsyncSessionLocal` in each `app/db/session.py`), so each `privileged_access_audit.py` hand-rolls a second, dedicated synchronous engine + `sessionmaker` purely so this one hook can call `.commit()` without `await`. This is 4 copies of the same ~8-line workaround, each holding its own live connection pool to a database the service already has an async pool for.

Because `get_validated_user` is a plain `def`, FastAPI runs it in its threadpool executor rather than on the event loop — which is *why* the sync workaround was viable in the first place, not an accident.

## Goals / Non-Goals

**Goals:**
- Eliminate the 4 duplicate synchronous connection pools.
- Make `log_privileged_access` and the registered sink async, writing through each service's existing `AsyncSessionLocal`.
- Preserve `privileged-access-audit`'s existing behavior exactly (what gets logged, fail-closed-for-writes/fail-open-for-reads semantics) — this is an internals-only change.

**Non-Goals:**
- No change to the `privileged_access_logs` schema, the audit payload shape, or the fail-open/fail-closed policy.
- No change to `customer-impersonation` or any other capability's behavior.
- Not migrating any service off async SQLAlchemy or onto it (ai/chat were already async before this change; nothing here changes that).

## Decisions

**1. Make `get_validated_user` an `async def`, not a background/threadpool dispatch trick.**
Alternative considered: keep it sync and bridge to the async sink via `asyncio.run_coroutine_threadsafe` (the pattern already used in `services/budget/app/services/event_consumer.py` for a sync pika callback thread). Rejected: `get_validated_user` already runs inside a live FastAPI/uvicorn event loop (unlike the pika callback, which runs on a separate OS thread with no loop of its own), so there's no cross-thread boundary to bridge — `async def` + `await` is the direct, idiomatic fix. FastAPI resolves `Depends()` async dependencies natively, and a full repo grep confirms every call site uses `Depends(get_validated_user)`; there are no direct/manual callers to update, and dependency-override tests (`app.dependency_overrides[get_validated_user] = lambda: user`) keep working since FastAPI doesn't require the override to match sync/async.

**2. `make_privileged_access_sink` takes an async `session_factory` and returns an `async def` sink; `log_privileged_access` becomes `async def` and awaits it directly (no `iscoroutinefunction` branching).**
Alternative considered: support both sync and async sinks in `log_privileged_access` (detect via `inspect.iscoroutinefunction`) to keep a migration path for any not-yet-async service. Rejected: verified all 4 services (`budget`, `users`, `ai`, `chat`) already run `create_async_engine`/`AsyncSessionLocal` as their primary session — there is no sync straggler today, so the branching would be speculative complexity with no current caller. If a 5th sync service ever needs this hook, that's the moment to add the branch, not now.

**3. Each service's `privileged_access_audit.py` imports its own `AsyncSessionLocal` from `app/db/session.py` instead of constructing a new engine.**
This is the direct payoff: `create_engine(settings.<x>_database_url)` + `sessionmaker(...)` is deleted from all 4 files, replaced by importing the existing async session factory already used for every other query in that service.

## Risks / Trade-offs

- [Risk] `get_validated_user` becoming `async def` changes it from running in FastAPI's threadpool to running directly on the event loop. If anything else in that function does blocking I/O (e.g. a slow synchronous call), it would now block the loop instead of a worker thread. → Mitigation: audit `get_validated_user`'s body as part of implementation; today its other work (JWT decode, claims lookup) is already fast/non-blocking, and this was already true for every other async route dependency in these services.
- [Risk] `shared/security/dependencies.py` and `shared/security/privileged_access.py` are auth-critical and imported by all 4 services — a mistake here is a cross-service outage, not a budget-only bug. → Mitigation: this repo already has a precedent outage from a shared-contract gap in claims handling (see JWT claims builder backlog); treat this change with the same care — full test pass across all 4 services' auth-dependent test suites before merge, not just budget's.
- [Risk] Losing the dedicated sync engine means audit writes now share connection-pool pressure with each service's primary async pool instead of having an isolated pool. → Mitigation: acceptable trade — the whole point of this change is that a dedicated pool per service was unnecessary duplication, and the primary pool already sizes for the service's real request volume.

## Migration Plan

1. Update `shared/security/privileged_access.py` (sink + `log_privileged_access` go async) and `shared/security/dependencies.py` (`get_validated_user` goes async).
2. Update each service's `privileged_access_audit.py` to register an async sink over its own `AsyncSessionLocal`, one service at a time, running that service's full test suite after each.
3. No data migration, no API contract change, no feature flag needed — this is an internal-only refactor behind an existing dependency boundary.

Rollback: revert the commit(s); no schema/data changes to unwind.

## Open Questions

- None — all 4 services confirmed already async; no branching or staged rollout required.
