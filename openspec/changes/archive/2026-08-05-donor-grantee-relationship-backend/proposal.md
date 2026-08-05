## Why

Today any grantee can attach any donor customer as `funding_customer_id` when creating or editing a budget — there is no check that the donor actually agreed to fund that grantee. In the real world a grantee can't just pick a donor; the donor has to establish the relationship first. This change adds that relationship as data (donor-owned, presence = approval) and gates budget funding on it.

## What Changes

- Add a `donor_grantees` table in the users service linking a donor `CustomerModel` to a grantee `CustomerModel`. Fix the model as currently drafted: drop its redundant shadow `id` (rely on `AuditMixin.id`), add a unique constraint on `(donor_id, grantee_id)`, and register it in `app/models/__init__.py` so Alembic autogenerate picks it up.
- Add users-service endpoints: donor creates a relationship (`donor_id` derived from the caller's JWT, never client-supplied), donor lists/deletes their own relationships, grantee lists (read-only) the donors that have approved them, and a no-auth internal `exists` check for service-to-service use (matching the existing `POST /customers/by_ids/` convention).
- Add a synchronous cross-service check in the budget service: before a budget's `funding_customer_id` is set (on both create and update), verify a `donor_grantees` row exists for that (donor, owner) pair. **BREAKING** for any existing workflow that sets `funding_customer_id` without a prior relationship — after this change such requests are rejected.
- Extend `GET /customers/` with optional `is_ngo`/`search` filters and add `Depends(get_current_user)` auth to `list_customers`/`get_customer_endpoint`, since a later frontend change will expose these through the public gateway for the first time.
- Add gateway routes for `/api/v1/donor-grantees/` (and `/api/v1/customers/`) in nginx.conf, nginx-dev.conf, and Caddyfile.

Frontend UI for managing/using this relationship (donor's grantee-management page, grantee's donor picker) is a separate, follow-up change (`donor-grantee-relationship-frontend`) and is out of scope here.

## Capabilities

### New Capabilities
- `donor-grantee-relationship`: donor-owned relationship records that gate which donor a grantee may attach to a budget as `funding_customer_id`. Covers the users-service CRUD + internal check endpoint and the budget-service enforcement at create/update time.

### Modified Capabilities
(none — no existing `openspec/specs/` capability currently documents `funding_customer_id` validation on budget create/update, so there is no existing spec requirement being changed, only new ones being added under the new capability above.)

## Impact

- **Users service**: `app/models/customer.py`, new migration, new `app/schemas/donor_grantee_schema.py`, `app/crud/donor_grantee_crud.py`, `app/api/donor_grantee_routes.py`, `main.py` router registration, `app/api/customer_routes.py` (filters + auth).
- **Budget service**: new `app/services/donor_grantee_client.py`, `app/services/budget_services.py` (both `create_budget_service` and `update_budget_service`), `app/core/config.py`, env files.
- **Gateway**: `nginx/nginx.conf`, `nginx/nginx-dev.conf`, `Caddyfile`.
- **Tests**: new users-service route tests, new budget-service gate tests.
- No frontend changes in this PR — existing frontend flows that set `funding_customer_id` (currently only via chat/AI, since there's no manual picker yet) will start failing until a relationship exists; this is acceptable since that path is not yet user-facing.
