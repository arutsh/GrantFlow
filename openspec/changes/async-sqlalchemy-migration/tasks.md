Workflow rule: **one task group = one GitHub ticket = one PR, merged before the next group starts.** This change supersedes backlog issues #70 (migrate budget+users to async SQLAlchemy) and #59 (CRUD `commit=False`/`flush()` support); file a fresh ticket per group below via `scripts/new-issue.sh` at implementation time and close #70/#59 from the groups noted, rather than reusing their numbers directly. Every PR: `flake8 --max-line-length=100` clean; commits/pushes only with explicit user approval.

## 0. AuditMixin timestamp defaults (shared prerequisite) — must land before either service sets `expire_on_commit`

- [ ] 0.1 Change `shared/db/audit_mixin.py`'s `created_at`/`updated_at` from DB-side `default=func.now()`/`onupdate=func.now()` to Python-side defaults (e.g. `default=lambda: datetime.now(timezone.utc)` for `created_at`; explicit assignment on update, matching `services/ai/app/crud/user_provider_key.py`'s pattern)
- [ ] 0.2 Grep budget/users CRUD and service modules for `session.refresh(...)` calls that exist solely to pick up `created_at`/`updated_at` after commit; confirm they're now redundant and drop them
- [ ] 0.3 Run each service's existing (sync) test suite to confirm no behavior change from the mixin edit alone, before any async/session work begins
- [ ] 0.4 Run `black`/`mypy`/`flake8 --max-line-length=100` clean; PR merged

## 1. Users-service async migration (dry run) — depends on 0, closes #70 (users half)

- [ ] 1.1 Swap `services/users/app/db/session.py` to `create_async_engine`/`async_sessionmaker`/`AsyncSession`, mirroring `services/ai/app/db/session.py`'s driver-forcing (`make_url(...).set(drivername="postgresql+asyncpg")`); keep psycopg2 available for Alembic only
- [ ] 1.2 Update `get_db()` in `services/users/app/db/session.py` to `async def`, yielding the `AsyncSession`
- [ ] 1.3 Convert every `services/users/app/crud/*.py` function from `.query(...)`/`session.commit()` to `select(...)`/`await db.execute(...)`/`await db.commit()`
- [ ] 1.4 Update every route in `services/users/app/api/*.py` to depend on `AsyncSession` and `await` all CRUD calls
- [ ] 1.5 Audit `services/users/app/models/*.py` relationships (`customer` already `lazy="joined"`; `sessions`, `users`, `donor`, `grantee` are default-lazy) and add `selectinload`/`joinedload` at each query site that actually reads one of them
- [ ] 1.6 Convert `services/users/tests/` fixtures/sessions to async, following `services/ai/tests`' existing async pattern
- [ ] 1.7 Run the full users-service test suite plus a manual smoke pass through every route; confirm no `MissingGreenlet` errors
- [ ] 1.8 Run `black`/`mypy`/`flake8 --max-line-length=100` clean; PR merged (`Closes #70` for the users-service portion)

## 2. Budget-service async migration — depends on 1, closes #70 (budget half)

- [ ] 2.1 Swap `services/budget/app/db/session.py` to `create_async_engine`/`async_sessionmaker`/`AsyncSession`, same pattern validated in group 1
- [ ] 2.2 Centralize `get_db()` in `services/budget/app/db/session.py` as `async def` (currently defined locally in `budget_routes.py`); remove the duplicate
- [ ] 2.3 Convert every `services/budget/app/crud/*.py` function from `.query(...)`/`session.commit()` to `select(...)`/`await db.execute(...)`/`await db.commit()`
- [ ] 2.4 Update every route in `services/budget/app/api/*.py` to depend on `AsyncSession` and `await` all CRUD/service calls
- [ ] 2.5 Audit `services/budget/app/models/*.py` relationships (~15 across `budget.py`, `report.py`, `mapping.py`, `budget_templates.py`, `currency_ledger.py`, all default-lazy) and add `selectinload`/`joinedload` at each query site that actually reads one of them
- [ ] 2.6 Convert `services/budget/tests/` fixtures/sessions to async
- [ ] 2.7 Run the full budget-service test suite plus a manual smoke pass through every route (including `/budgets/with-lines`); confirm no `MissingGreenlet` errors
- [ ] 2.8 Run `black`/`mypy`/`flake8 --max-line-length=100` clean; PR merged (`Closes #70` for the budget-service portion)

## 3. Atomic multi-step writes (commit=False/flush) — depends on 2, closes #59

- [ ] 3.1 Add `commit: bool = True` to budget-service CRUD write functions (`create_budget`, `create_budget_line`, `delete_budget`, `delete_budget_line`, etc.); when `False`, call `await db.flush()` instead of `await db.commit()`; confirm no existing caller's behavior changes when the argument is omitted
- [ ] 3.2 Rewire `create_budget_with_lines_service` (`services/budget/app/services/budget_services.py:503-566`) to call `create_budget_service`/`create_budget_line_service` with `commit=False`, issue a single `await db.commit()` after all lines are created, and delete the compensating `delete_budget_line`/`delete_budget` rollback calls in the `except` blocks (rely on transaction rollback instead)
- [ ] 3.3 Add tests: default-`commit=True` callers behave exactly as before; `create_budget_with_lines_service` issues exactly one commit across the whole operation; a forced mid-loop failure (e.g. a bad line triggering a DB constraint error) leaves zero rows committed for the budget and its lines, verified by querying the DB after the failed call
- [ ] 3.4 Run `black`/`mypy`/`flake8 --max-line-length=100` clean; PR merged (`Closes #59`)
