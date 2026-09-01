## Why

`shared/db/audit_mixin.py`'s `AuditMixin` provides `created_by`/`updated_by`, but nothing in the codebase actually populates them reliably: there is no request-scoped current-user context and no SQLAlchemy event hook, so every CRUD function that wants an audit trail must manually thread a `user_id` parameter. This has already produced two classes of bug — `updated_by` on 8 budget models is set once at creation and never refreshed on edit, and 3 models (`ReportLineConversionAllocationModel`, `BugReportModel`, `DonorGranteeModel`) declare the columns but leave them permanently NULL. Any further rollout of `AuditMixin` to more models (tracked as separate follow-on changes) would just create more instances of the same silent gap unless population is made automatic first. Separately, `AuditMixin` hardcodes `id` as primary key, which structurally blocks 2 models with custom PKs (`CustomerAiDefaults.customer_id`, `UserProfileModel.user_id`) from adopting it at all.

## What Changes

- Add a request-scoped `ContextVar[uuid.UUID | None]` holding the current user's id, set once per request by a shared FastAPI dependency/middleware built on top of `shared/security/dependencies.py`.
- Add a SQLAlchemy mapper-level event listener bound to `AuditMixin` (`before_insert` sets `created_by`; `before_insert` and `before_update` set `updated_by`) that reads the contextvar automatically, replacing manual per-CRUD `user_id` assignment.
- Wire the dependency and event listener into all 4 services' app/session setup: `services/ai`, `services/budget`, `services/chat`, `services/users`.
- Ensure the contextvar resolves to `None` (not an exception) on paths with no request context — Celery worker tasks, seed/migration scripts, unauthenticated endpoints — with an explicit test covering at least one such path.
- Split `shared/db/audit_mixin.py`'s `AuditMixin` into the existing `id`-bearing `AuditMixin` (unchanged behavior for current 11 adopters) plus a new PK-less `AuditColumnsMixin` (`created_at`/`updated_at`/`created_by`/`updated_by` only) for models with non-`id` primary keys.
- Remove the now-redundant manual `created_by=`/`updated_by=` assignments in the 8 budget CRUD functions that set them today, relying on the event listener instead.

## Capabilities

### New Capabilities
- `model-audit-trail`: automatic, request-scoped population of `created_by`/`updated_by` audit columns for any model using `AuditMixin`/`AuditColumnsMixin`, via a ContextVar + SQLAlchemy event listener, applied consistently across all 4 services.

### Modified Capabilities
(none — no existing spec currently documents `created_by`/`updated_by` behavior)

## Impact

- `shared/db/audit_mixin.py` (split into two mixins), `shared/security/dependencies.py` (or a new sibling module) for the contextvar-setting dependency.
- Session/app startup wiring in `services/ai/app`, `services/budget/app`, `services/chat/app`, `services/users/app`.
- CRUD functions in `services/budget/app/crud/*.py` that currently set `created_by`/`updated_by` manually (8 models) — assignments removed, behavior preserved via the event listener.
- No database migration needed — this change only affects how existing columns get populated, not schema.
- No FK constraint is added from `created_by`/`updated_by` to the users table — that's intentional, since users live in a separate service/database.
