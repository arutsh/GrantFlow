## Why

Admins have no self-service way to invite teammates, remove users, or update their own company's details — the `company-onboarding` capability explicitly flagged self-service invitation as out of scope, leaving it as "only a superuser can assign another user's `customer_id`/`role`" (`openspec/specs/company-onboarding/spec.md`). Today that means direct DB access for routine account admin. Superusers need the equivalent power across *any* company (support, corrections, offboarding) — the shipped `customer-impersonation` capability (formerly `superuser-cross-tenant-access`) is what makes that possible without duplicating endpoints; see design.md.

## What Changes

- Add an admin-only "Company Management" page (frontend) covering the admin's own company:
  - Invite a new user to the company (creates a pending user; invitee sets a password via a token-based accept-invite link, reusing the email-verification token pattern)
  - Remove a user from the company (soft-delete/anonymize, reusing the GDPR erasure path)
  - Promote/demote a user between `admin` and `user` within the company, subject to a last-admin protection
  - Update the company's own details (name, country, currency, is_ngo, is_donor)
- Add a superuser-only company **deactivation** capability, reachable either directly (real `superuser` role) or while impersonating the target company — this is the one action deliberately excluded from what a company's own admin can do to itself.
- Superusers get invite/remove-user/promote-demote/update-company for *any* company for free by starting an impersonation session (per `customer-impersonation`) and using the same admin endpoints above — no dedicated superuser-scoped endpoints for these four actions.
- New/changed backend endpoints in `services/users`: user invite, user removal (admin-scoped, distinct from the existing self-delete `DELETE /users/{user_id}` in `user_routes.py`), user role update, company update, company deactivate (superuser/impersonation-only).
- New guard in `services/users/app/crud/donor_grantee_crud.py`: reject `donor_id == grantee_id`, a self-referential relationship newly reachable now that a company can self-configure `is_ngo`/`is_donor` as both true.

## Capabilities

### New Capabilities
- `company-user-administration`: admins invite/remove/promote-demote users within their own company, and update their own company's details, including `is_ngo`/`is_donor`.
- `superuser-tenant-administration`: superuser-only company deactivation, plus the impersonation-based path for exercising `company-user-administration` against any company.

### Modified Capabilities
- `company-onboarding`: removes the "no self-service invitation mechanism exists yet" gap called out in its current spec.
- `donor-grantee-relationship`: adds a guard rejecting self-referential (`donor_id == grantee_id`) relationships.

## Impact

- **Code**: `services/users/app/api/user_routes.py` (new admin-scoped user endpoints, distinct from self-service ones), `services/users/app/api/customer_routes.py` (new update/deactivate endpoints — currently only create/list/get exist), `services/users/app/crud/user_crud.py`, `services/users/app/crud/customer_crud.py`, `services/users/app/crud/donor_grantee_crud.py` (self-reference guard), `services/users/app/models/customer.py` (deactivation fields).
- **Frontend**: new admin Company Management page in `frontend-typescript`, plus a superuser company picker that starts an impersonation session and routes into the same page.
- **Relation to `customer-impersonation`**: resolved — `customer-impersonation` shipped and archived (2026-08-17) before this change was implemented. Its `/auth/impersonate` mints a token with `role: "admin"` scoped to the target `customer_id`, so the admin endpoints in `company-user-administration` are reachable by an impersonating superuser with no extra code. Only company deactivation needs an explicit `role == "superuser" or is_impersonating` check, since it's the one action a plain admin must not be able to do to their own company. See design.md.
- **Deferred, not in this change**: cross-service enforcement of company deactivation (`services/budget`, `services/reports` don't check customer status, so an already-issued token from a deactivated company's user keeps working until it expires); role-gating on who within a donor company can approve a grantee (currently any authenticated user of a donor customer); an audit/action log for admin actions (tracked alongside the pre-existing budget-status-history backlog, GitHub #138).
