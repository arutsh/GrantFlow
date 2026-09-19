One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Shared audit-trail infrastructure

- [x] 1.1 Add `shared/security/current_user_context.py` with a `ContextVar[uuid.UUID | None]` (default `None`) and a small `set`/reset helper.
- [x] 1.2 In `shared/db/audit_mixin.py`, split `AuditMixin` into the existing `id`-bearing `AuditMixin` plus a new PK-less `AuditColumnsMixin` (`created_at`/`updated_at`/`created_by`/`updated_by` only), sharing common column definitions.
- [x] 1.3 Register a SQLAlchemy mapper event listener at import time in `shared/db/audit_mixin.py` (`before_insert` sets `created_by`/`updated_by` from the contextvar; `before_update` sets `updated_by`), bound with `propagate=True` so it applies to both mixins and every subclass.
- [x] 1.4 Unit test the listener logic in isolation (in-memory sqlite, a throwaway test model per mixin) covering: contextvar set → columns populated; contextvar unset (`None`) → columns stay `NULL`, no exception.
- [x] 1.5 Run `shared`'s test suite clean; PR merged. (112 passed, 1 pre-existing unrelated worktree-scanning failure; merged per group-1 confirmation)
- [x] 1.6 Scope `before_update`'s `updated_by` assignment to fire only when a tracked column actually changed (not on relationship-only dirty state), per design.md Decision 6. Add a test asserting a relationship-only mutation does NOT update `updated_by`.

## 2. Wire current-user capture into the shared auth dependency — depends on 1

- [x] 2.1 In `shared/security/dependencies.py`, set the contextvar (with a reset in a `finally`) as a side effect of `get_validated_user`/`get_current_user`, immediately after JWT decoding succeeds. (Converted both from `def` to `async def`/async-generator — a plain `def` FastAPI dependency runs in a threadpool with its own copied context, so a `.set()` inside it never propagates to the endpoint/flush. `get_current_user` is now an async generator yielding the payload, resetting the contextvar in a `finally`; `get_validated_user` stays a plain coroutine. Updated the 11 direct-call tests in `shared/tests/test_dependencies.py` to `@pytest.mark.anyio async def`.)
- [x] 2.1.1 Follow-up found in review: the `async def` conversion left `is_session_revoked` on its old sync `redis` client, wrapped in `run_in_threadpool` on every request. Migrated `shared/security/session_revocation.py` to `redis.asyncio` (matching `services/ai/app/services/rate_limiter.py`), removing the threadpool hop entirely; updated all `mark_session_revoked` call sites to `await`, including fixing the already-broken `revoke_unverified_sessions` maintenance script (its `SessionLocal` import predates the sync→async users-service migration in `64ce555`) to run on `AsyncSessionLocal`. See design.md Risks.
- [x] 2.2 / 2.3 Add end-to-end test(s) against a real engine asserting a request through `Depends(get_validated_user)` populates `created_by`. (Collapsed into one test: `services/budget` and `services/users` were migrated to async SQLAlchemy in `64ce555`, before this change — design.md's "budget/users are sync" framing is stale, so there is no sync-engine service left to test against. `shared/tests/test_audit_context_propagation_e2e.py` covers the async-engine + real-auth-chain scenario, which is now the only one that exists.)
- [x] 2.4 Add a test confirming a Celery-style call with no request/dependency context leaves `created_by`/`updated_by` `NULL` without raising. (Already covered by `test_audit_mixin.py::TestAuditMixinListener::test_created_by_stays_null_when_context_unset` from group 1 — a direct ORM insert with no contextvar set and no FastAPI request is exactly the Celery-worker shape; no new test needed.)
- [x] 2.5 Run `shared`'s test suite clean; PR merged. (117 passed [+5 net new], 1 pre-existing unrelated worktree-scanning failure; all 4 services' own suites also re-run clean: budget 369, users 194, ai 121, chat 92. PR not yet opened.)

## 3. Enable in budget service — depends on 1, 2

- [x] 3.1 Resolved at design stage (design.md Decision 5): manual assignments confirmed redundant/in-sync with the automatic listener across all 4 services, no on-behalf-of divergence found. No per-call-site removal needed.
- [ ] 3.2 (dropped — manual assignments stay in place per Decision 5; not removed)
- [ ] 3.3 Add/update a test proving the previously-stale-`updated_by` bug is fixed: create a row as user A, update it as user B, assert `updated_by` now equals B (not still A).
- [ ] 3.4 Run `services/budget`'s test suite clean; PR merged.

## 4. Enable in users service — depends on 1, 2

- [ ] 4.1 Verify `DonorGranteeModel` and `BugReportModel` (both already use `AuditMixin` but currently leave the columns `NULL`) now get `created_by`/`updated_by` populated automatically with no CRUD changes needed.
- [ ] 4.2 Add regression tests for both models asserting `created_by` is populated on creation via their existing routes.
- [ ] 4.3 Run `services/users`'s test suite clean; PR merged.
