Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Resolve open design questions

- [ ] 1.1 Decide the invite mechanism (pending `UserModel` row vs. separate invite-token table; reuse `email_verification_token_hash`/`email-verification` capability or a new token type) — update design.md
- [ ] 1.2 Decide user-removal semantics (hard delete vs. reuse the GDPR soft-delete/anonymization path on `UserModel`) — update design.md
- [ ] 1.3 Decide company-delete semantics (hard delete, soft-delete/deactivate, or blocked while active users/budgets/reports exist across services) — update design.md
- [ ] 1.4 Decide role boundaries (can an admin remove/demote another admin, including self; is at least one admin required per company) — update design.md
- [ ] 1.5 Decide which company fields are admin-editable vs. superuser-only (e.g. `is_ngo`/`is_donor`) — update design.md
- [ ] 1.6 Decide whether `superuser-tenant-administration` is implemented as dedicated superuser-scoped endpoints or as impersonation (from `superuser-cross-tenant-access`) plus reuse of `company-user-administration` endpoints — update design.md and, if it changes scope, the `superuser-tenant-administration` spec
- [ ] 1.7 PR merged (docs-only: design.md + spec updates)

## 2. Backend: company-user-administration — depends on 1

- [ ] 2.1 Add admin-scoped invite endpoint in `services/users/app/api/user_routes.py` per the mechanism decided in 1.1
- [ ] 2.2 Add admin-scoped user-removal endpoint (distinct from the existing self-service `DELETE /users/{user_id}`), scoped to the admin's own `customer_id`, per semantics decided in 1.2
- [ ] 2.3 Add company-update endpoint in `services/users/app/api/customer_routes.py`, scoped to the admin's own `customer_id`, restricted to the fields decided in 1.5
- [ ] 2.4 Tests: admin can invite/remove users and update company details within their own `customer_id`; cannot act on another company's users/details; non-admin roles are rejected
- [ ] 2.5 Run users-service test suite and flake8 (`--max-line-length=100`) clean; PR merged

## 3. Frontend: Company Management page (admin) — depends on 2

- [ ] 3.1 Add an admin-only "Company Management" page listing the company's users, with invite and remove actions
- [ ] 3.2 Add a form to update the company's own editable details
- [ ] 3.3 Tests: page and actions are hidden/inaccessible for non-admin roles
- [ ] 3.4 Run frontend test suite and lint clean; PR merged

## 4. Superuser tenant administration — depends on 1, 2, 3

- [ ] 4.1 Implement per the mechanism decided in 1.6: either dedicated superuser-scoped endpoints (mirroring 2.1-2.3 but unbound from `customer_id`) and UI (company picker + reuse of the page from group 3), or the impersonation-session path plus a company picker only
- [ ] 4.2 Add company-delete capability (superuser-only per current spec) per semantics decided in 1.3
- [ ] 4.3 Tests: superuser can act on any company's users/details, including delete; non-superuser roles are rejected
- [ ] 4.4 Run affected services' test suites, flake8 (`--max-line-length=100`), and frontend lint clean; PR merged
