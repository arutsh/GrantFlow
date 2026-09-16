## ADDED Requirements

### Requirement: End-to-end async database access
Budget-service and users-service SHALL perform all database reads and writes through an async SQLAlchemy engine and session (`create_async_engine` + `AsyncSession` via `async_sessionmaker`), with no route or service-layer function depending on a sync `Session`/`SessionLocal`. Alembic migrations MAY continue to run synchronously against the same database.

#### Scenario: Route handler receives an async session
- **WHEN** any request hits a budget-service or users-service route that reads or writes the database
- **THEN** the route's `db` dependency is a `AsyncSession` obtained via `Depends(get_db)`, and every DB call in the request path is awaited (`await db.execute(...)`, `await db.commit()`, `await db.flush()`)

#### Scenario: No sync engine remains reachable from application code
- **WHEN** the codebase is searched for `create_engine(` or `sessionmaker(` (sync forms) in `services/budget/app` or `services/users/app`
- **THEN** no application code path (routes, services, CRUD) references them; only Alembic's own migration runner may still use a sync connection

### Requirement: No lazy-load MissingGreenlet risk
Every SQLAlchemy relationship that a route or service function reads SHALL be either explicitly eager-loaded at the query site (`selectinload`/`joinedload`) or never accessed outside an awaited context. No request path SHALL trigger an implicit lazy-load under the async session.

#### Scenario: Relationship access on an already-loaded object
- **WHEN** a route or service function accesses a model's relationship attribute (e.g. `budget.lines`, `user.customer`) after fetching that model
- **THEN** the query that fetched the model explicitly eager-loaded that relationship, so the attribute access does not trigger a lazy SQL query

#### Scenario: Full test and manual smoke pass surfaces no MissingGreenlet
- **WHEN** the full test suite for a migrated service runs, and every route is manually exercised once
- **THEN** no `MissingGreenlet` (or equivalent lazy-load-under-async) error occurs

### Requirement: Timestamp correctness under expire_on_commit=False
`AuditMixin`-backed models SHALL set `created_at`/`updated_at` in Python before a write is committed, not rely on a database-computed default (`func.now()`/`onupdate`) that requires a post-commit refresh to observe. No route or service function SHALL depend on an explicit `session.refresh()`/`await session.refresh()` call to obtain a correct audit timestamp.

#### Scenario: Created row has a correct timestamp with no refresh
- **WHEN** a route creates an `AuditMixin`-backed row and returns it in the response without calling `refresh()`
- **THEN** the response's `created_at` reflects the actual creation time, not `None` or a stale value

#### Scenario: Updated row has a correct timestamp with no refresh
- **WHEN** a route updates an `AuditMixin`-backed row and returns it in the response without calling `refresh()`
- **THEN** the response's `updated_at` reflects the actual update time, not the prior value

### Requirement: Atomic multi-step writes via commit=False
CRUD write functions SHALL accept an optional `commit: bool = True` parameter. When `commit=False`, the function SHALL call `session.flush()` instead of `session.commit()`, leaving the caller responsible for the final commit. The default (`commit=True`) SHALL preserve every existing caller's current commit-per-call behavior unchanged.

#### Scenario: Default caller behavior is unchanged
- **WHEN** an existing caller invokes a CRUD write function without passing `commit`
- **THEN** the function commits immediately, exactly as it did before this change

#### Scenario: Multi-step write commits once
- **WHEN** `create_budget_with_lines_service` creates a budget and its lines
- **THEN** each inner CRUD call is invoked with `commit=False` (flushing only), and a single `db.commit()` is issued once after all lines are created, making the whole operation atomic in one DB transaction

#### Scenario: Failure mid-transaction rolls back, not compensating-deletes
- **WHEN** `create_budget_with_lines_service` encounters an error after the budget and some lines have been flushed but before the final commit
- **THEN** the transaction is rolled back (no committed rows for the budget or any of its lines) instead of issuing explicit `delete_budget_line`/`delete_budget` calls to undo already-committed rows
