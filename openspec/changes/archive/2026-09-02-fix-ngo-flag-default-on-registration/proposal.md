## Why

Self-service company registration (founder onboarding) silently creates every new company with `is_ngo=False`, even though the model's declared default is `True`. Because donor search and grant-receiving checks filter on `is_ngo=true`, newly registered NGOs are invisible to donors and cannot receive grants until an admin manually flips the flag in Settings — a defect newly registered organizations have no way to discover on their own.

## What Changes

- Fix the self-service onboarding path (`PATCH /users/{user_id}/` with `new_customer_name`) so every new company it creates has `is_ngo=True`, matching the model's intended default.
- Fix `create_customer` in `customer_crud.py`, whose parameter default (`is_ngo: bool = False`) is what actually overrides the model default today; align it so callers that don't specify `is_ngo` get `True`, not `False`.
- Reconcile the DB-level `server_default` (currently `"false"`, set by an earlier migration) with the intended `True` default, so the schema-level default matches application behavior.
- Leave the admin-only `POST /customers/` path unchanged — it already passes `is_ngo` explicitly from the request body and is not affected by this bug.
- Out of scope: backfilling `is_ngo` for companies that already self-registered with the flag incorrectly `False`. That's a data-remediation decision (which existing companies are actually NGOs vs. legitimately not) that needs an explicit call, not a blind migration — flagged in design.md for a follow-up decision, not executed here.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `company-onboarding`: adds a requirement that self-service onboarding via `new_customer_name` SHALL create the new company with `is_ngo=True`.

## Impact

- **Backend (services/users)**:
  - `app/api/user_routes.py` — onboarding call site to `create_customer`.
  - `app/crud/customer_crud.py` — `create_customer`'s `is_ngo` parameter default.
  - `app/models/customer.py` — `CustomerModel.is_ngo` (confirm/keep `default=True`).
  - `migrations/versions/` — new migration to align `server_default` with `True`.
- **Downstream consumers unaffected but validated by this fix**:
  - Donor grantee search (`GET /customers/?is_ngo=true`, `ManageGrantees.tsx`).
  - `services/budget/app/services/customer_client.py`'s grant-receiving `is_ngo` assertion.
- **No frontend changes** — the Settings NGO checkbox and admin-created-customer flow already behave correctly; this only fixes the self-service registration default.
