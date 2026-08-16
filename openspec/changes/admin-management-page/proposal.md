## Why

Admins have no self-service way to invite teammates, remove users, or update their own company's details — the `company-onboarding` capability explicitly flagged self-service invitation as out of scope, leaving it as "only a superuser can assign another user's `customer_id`/`role`" (`openspec/specs/company-onboarding/spec.md`). Today that means direct DB access for routine account admin. Superusers need the equivalent power across *any* company (support, corrections, offboarding), which overlaps with the in-flight `superuser-cross-tenant-access` impersonation change — see Open Questions for how these two relate.

## What Changes

- Add an admin-only "Company Management" page (frontend) covering the admin's own company:
  - Invite a new user to the company (creates a pending user, sends an invite — mechanism TBD, see Open Questions)
  - Delete a user from the company
  - Update the company's own details (name, country, currency, is_ngo/is_donor)
- Add superuser-only capability to do the same across **any** company: delete/update any user, delete/update any company, not just their own.
- New/changed backend endpoints in `services/users`: user invite, user delete (admin/superuser-only, distinct from the existing self-delete `DELETE /users/{user_id}` in `user_routes.py`), company update, company delete.

## Capabilities

### New Capabilities
- `company-user-administration`: admins invite/remove users within their own company, and update their own company's details.
- `superuser-tenant-administration`: superusers delete/update any user and any company across tenants.

### Modified Capabilities
- `company-onboarding`: removes the "no self-service invitation mechanism exists yet" gap called out in its current spec.

## Impact

- **Code**: `services/users/app/api/user_routes.py` (new admin-scoped user endpoints, distinct from self-service ones), `services/users/app/api/customer_routes.py` (new update/delete endpoints — currently only create/list/get exist), `services/users/app/crud/user_crud.py`, `services/users/app/crud/customer_crud.py`.
- **Frontend**: new admin/superuser management page(s) in `frontend-typescript`.
- **Relation to `superuser-cross-tenant-access`**: that change is building session-level impersonation so a superuser can act as any customer through the existing app unmodified. Whether superuser tenant-administration here should be its own set of superuser-scoped endpoints, or should simply be the admin endpoints above exercised through an impersonation session, is an open question — see design.md.
