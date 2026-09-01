One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Shared audit-trail infrastructure

- [ ] 1.1 Add `shared/security/current_user_context.py` with a `ContextVar[uuid.UUID | None]` (default `None`) and a small `set`/reset helper.
- [ ] 1.2 In `shared/db/audit_mixin.py`, split `AuditMixin` into the existing `id`-bearing `AuditMixin` plus a new PK-less `AuditColumnsMixin` (`created_at`/`updated_at`/`created_by`/`updated_by` only), sharing common column definitions.
- [ ] 1.3 Register a SQLAlchemy mapper event listener at import time in `shared/db/audit_mixin.py` (`before_insert` sets `created_by`/`updated_by` from the contextvar; `before_update` sets `updated_by`), bound with `propagate=True` so it applies to both mixins and every subclass.
- [ ] 1.4 Unit test the listener logic in isolation (in-memory sqlite, a throwaway test model per mixin) covering: contextvar set → columns populated; contextvar unset (`None`) → columns stay `NULL`, no exception.
- [ ] 1.5 Run `shared`'s test suite clean; PR merged.

## 2. Wire current-user capture into the shared auth dependency — depends on 1

- [ ] 2.1 In `shared/security/dependencies.py`, set the contextvar (with a reset in a `finally`) as a side effect of `get_validated_user`/`get_current_user`, immediately after JWT decoding succeeds.
- [ ] 2.2 Add an end-to-end test against a real **sync** engine (mirrors `budget`/`users`) asserting a request through a route using `Depends(get_validated_user)` results in `created_by` being populated on insert for a mixin-using test model.
- [ ] 2.3 Add the equivalent end-to-end test against a real **async** engine (mirrors `ai`/`chat`) — this is the test that validates contextvar propagation through SQLAlchemy's async `greenlet_spawn` and Starlette's threadpool-executed sync dependencies, per the design doc's risk section.
- [ ] 2.4 Add a test confirming a Celery-style call with no request/dependency context leaves `created_by`/`updated_by` `NULL` without raising.
- [ ] 2.5 Run `shared`'s test suite clean; PR merged.

## 3. Enable in budget service — depends on 1, 2

- [ ] 3.1 Audit each of the 8 CRUD functions in `services/budget/app/crud/*.py` that currently set `created_by=`/`updated_by=` manually; confirm none pass a `user_id` that differs from the authenticated request's user (per design.md's open question).
- [ ] 3.2 Remove the manual assignments confirmed redundant in 3.1, relying on the automatic listener; keep an explicit override only where 3.1 found a legitimate on-behalf-of case.
- [ ] 3.3 Add/update a test proving the previously-stale-`updated_by` bug is fixed: create a row as user A, update it as user B, assert `updated_by` now equals B (not still A).
- [ ] 3.4 Run `services/budget`'s test suite clean; PR merged.

## 4. Enable in users service — depends on 1, 2

- [ ] 4.1 Verify `DonorGranteeModel` and `BugReportModel` (both already use `AuditMixin` but currently leave the columns `NULL`) now get `created_by`/`updated_by` populated automatically with no CRUD changes needed.
- [ ] 4.2 Add regression tests for both models asserting `created_by` is populated on creation via their existing routes.
- [ ] 4.3 Run `services/users`'s test suite clean; PR merged.
