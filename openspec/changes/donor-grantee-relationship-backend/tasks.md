One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Users-service donor-grantee relationship — ticket #189 (`Users/Issue-189/donor-grantee-relationship`)

- [x] 1.1 Fix `DonorGranteeModel` in `services/users/app/models/customer.py`: drop its shadowing `id` column (rely on `AuditMixin.id`), add `__table_args__ = (UniqueConstraint("donor_id", "grantee_id", name="uq_donor_grantees_donor_grantee"),)`.
- [x] 1.2 Register `DonorGranteeModel` in `services/users/app/models/__init__.py` so Alembic autogenerate picks it up (verify via `services/users/migrations/env.py`'s `from app.models import *`).
- [x] 1.3 Generate and review migration `services/users/migrations/versions/000004_add_donor_grantees.py` (`down_revision = "000003"`): `donor_grantees` table with `id`, `donor_id`/`grantee_id` (FK `customers.id`), `AuditMixin` audit columns, the unique constraint, and indexes on `donor_id` and `grantee_id`.
- [x] 1.4 Add `services/users/app/schemas/donor_grantee_schema.py`: `DonorGrantee` (response) and `DonorGranteeCreate` (`grantee_id` only — no `donor_id` field).
- [x] 1.5 Add `services/users/app/crud/donor_grantee_crud.py`: `create_donor_grantee`, `list_donor_grantees(*, donor_id=None, grantee_id=None)`, `get_donor_grantee`, `delete_donor_grantee`, `donor_grantee_exists`. `create_donor_grantee` fetches both the real donor and grantee `CustomerModel` rows in a single `get_customers_by_ids` query (keyed by `str(id)` to sidestep `GUID`'s dialect-dependent str/UUID round-trip) so the model's `@validates` hooks fire, and raises a 404-appropriate error if either customer doesn't exist.
- [x] 1.6 Add `services/users/app/api/donor_grantee_routes.py` following `customer_routes.py` conventions:
  - `POST /donor-grantees/` — donor-only (`require_donor` check on `valid_user`), `donor_id` always taken from `valid_user["customer_id"]`, never from the request body — **except for a `superuser` caller, who must supply `donor_id` explicitly in the body (rejected with 400 if omitted)**, since a superuser has no donor customer of their own to derive it from; 400 on duplicate (unique-constraint `IntegrityError`) or invalid grantee.
  - `GET /donor-grantees/?role=donor|grantee` — returns the caller's own relationships, scoped by their `customer_id`; 400 on missing/invalid `role`. A `superuser` caller must instead pass `customer_id` explicitly (rejected with 400 if omitted) and gets that customer's relationships.
  - `DELETE /donor-grantees/{id}` — donor-only; 404 if missing, 403 if `donor_id` doesn't match the caller. A `superuser` caller bypasses the ownership check and may delete any record.
  - `GET /donor-grantees/exists?donor_id=&grantee_id=` — no auth, matching the existing `POST /customers/by_ids/` internal-endpoint convention; returns `{"exists": bool}`.
- [x] 1.7 Register the router in `services/users/main.py` at prefix `/api`.
- [x] 1.8 Add test fixture support: extend `services/users/tests/conftest.py`'s `make_client` (or add a sibling fixture) to override `get_validated_user`, following the pattern already used in `services/budget/tests/conftest.py` with `ValidUserFactory`.
- [x] 1.9 Add `services/users/tests/` route tests covering: donor creates relationship; non-donor/grantee create is rejected; create against a non-NGO target is rejected; duplicate create is rejected; donor lists their own relationships; grantee lists their own (read-only) relationships; donor deletes their own relationship; donor cannot delete another donor's relationship; `exists` endpoint returns true/false correctly.
- [x] 1.10 Run users-service tests and lint clean; PR merged (`Closes` the ticket for this group).

## 2. Budget-service funding gate — depends on 1 — ticket #190 (`Budget/Issue-190/donor-grantee-funding-gate`)

- [x] 2.1 Add `donor_grantee_service_url` to `services/budget/app/core/config.py` and the corresponding env var to `.env.budget.private.local`, `.env.budget.prod`, `.env.budget.private.dev`, following the existing `CUSTOMER_SERVICE_URL` pattern (resolves to the users-service `/api/donor-grantees/` base).
- [x] 2.2 Add `services/budget/app/services/donor_grantee_client.py`: `check_donor_grantee_relationship(donor_id, grantee_id) -> bool` (sync `requests`, no auth header, no caching — deliberately, so revocation takes effect immediately) and `validate_donor_grantee_relationship(donor_id, grantee_id, raise_domain_error=False)`.
- [x] 2.3 Wire the check into `create_budget_service` (`services/budget/app/services/budget_services.py`): call `validate_donor_grantee_relationship(funding_customer_id, owner_id)` after `owner_id` is fully resolved (including the superuser-override branch), only when `funding_customer_id` is set.
- [x] 2.4 Wire the same check into `update_budget_service`: call it after `_resolve_updatable_budget` resolves `valid_budget.owner_id`, whenever the update sets/changes `funding_customer_id`.
- [x] 2.5 Add `services/budget/tests/test_donor_grantee_gate.py` (mirroring `test_customer_validation.py`'s style, patching `donor_grantee_client.check_donor_grantee_relationship`) plus cases in the existing create/update budget-service tests asserting `DomainError` when the relationship check fails, covering both `create_budget_service` and `update_budget_service` (including the "attach funder via PATCH" bypass scenario).
- [ ] 2.6 Run budget-service tests and lint clean; PR merged (`Closes` the ticket for this group).

## 3. Customer discovery + gateway routes — depends on 1 — ticket #191 (`Platform/Issue-191/customer-discovery-gateway-routes`)

- [ ] 3.1 Extend `get_customers`/`list_customers` (`services/users/app/crud/customer_crud.py`, `services/users/app/api/customer_routes.py`) with optional `is_ngo` and `search` (name `ilike`) query params.
- [ ] 3.2 Add `Depends(get_current_user)` to `list_customers` and `get_customer_endpoint` in `customer_routes.py` (currently unauthenticated; hardening ahead of exposing these through the public gateway for the first time).
- [ ] 3.3 Add gateway routes for `/api/v1/donor-grantees/` and `/api/v1/customers/` in `nginx/nginx-dev.conf`, `nginx/nginx.conf`, and `Caddyfile`, mirroring the existing `/api/v1/users/` block.
- [ ] 3.4 Manually verify (per design.md's migration plan) end-to-end against the dev stack: donor approves a grantee, grantee's budget-funding attempt succeeds; donor revokes, a new funding attempt fails while the earlier budget is unaffected; non-donor/grantee-side write attempts are rejected.
- [ ] 3.5 Run users-service tests and lint clean; PR merged (`Closes` the ticket for this group).
