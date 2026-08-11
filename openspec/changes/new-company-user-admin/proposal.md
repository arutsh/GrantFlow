## Why

When a new user completes onboarding by naming a brand-new company (via `PATCH /users/{id}` with `new_customer_name`), the users service creates the `CustomerModel` row and attaches it to the user, but leaves the user's role at the registration default (`user`). The person who just created the company has no way to manage it — invite teammates, configure org-level AI settings (gated on `admin`/`superuser` in `services/ai/app/api/settings_routes.py`), or otherwise administer the account they founded — until a superuser manually promotes them. The founder of a company should be its admin by default.

## What Changes

- When onboarding creates a brand-new customer via `new_customer_name`, the founding user's `role` is set to `admin` as part of the same update — no separate promotion step required.
- This role promotion applies only to the "create a new company" path. Joining an existing company via `customer_id` is unaffected and keeps today's behavior (role unchanged, defaults to `user`).
- The role assigned is exactly `admin` (org-level admin), not `superuser` (platform-level), which stays reserved for platform staff.
- This makes the founder's `admin` role immediately meaningful, not just a label: `services/ai/app/api/settings_routes.py` already gates org-level AI provider/key settings on `role in {"admin", "superuser"}`, so the founder can configure BYOK settings for their org the moment onboarding finishes, with no other change needed.
- Explicitly out of scope: inviting/promoting *other* teammates to a company. No such capability exists yet anywhere in the codebase (only a superuser can currently reassign `role`/`customer_id` via `PATCH /users/{id}`) — this change only fixes the founder's own role at company-creation time, and team invitation is flagged as known follow-on work, not built here.

## Capabilities

### New Capabilities
- `company-onboarding`: covers the non-superuser self-service flow where a user attaches themselves to a company during onboarding — either by creating a brand-new one (becoming its admin) or joining an existing one by `customer_id` (role unchanged).

### Modified Capabilities
(none — no existing spec currently documents this behavior)

## Impact

- `services/users/app/api/user_routes.py`: `update_user_endpoint`, the `new_customer_name` branch (currently ~lines 106-113) — add `role = "admin"` to the update alongside the existing `status = "active"` and new `customer_id`, bypassing the non-superuser `allowed_fields` restriction the same way `customer_id` already does.
- No schema, migration, or frontend changes needed — `UserRole.admin` already exists, `Onboarding.tsx` already refreshes the token after the PATCH succeeds, and `/auth/refresh` already re-reads the user's current DB role onto the new JWT.
- No change to `/register` or the login/refresh token-building logic.
