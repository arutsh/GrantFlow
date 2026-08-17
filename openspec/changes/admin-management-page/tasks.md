Workflow rule: one task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Resolve open design questions

- [x] 1.1 Decide the invite mechanism — pending `UserModel` row + reused email-verification token pattern, new accept-invite endpoint (design.md decision 3)
- [x] 1.2 Decide user-removal semantics — reuse the GDPR soft-delete/anonymization path (design.md decision 4)
- [x] 1.3 Decide company-delete semantics — soft-delete/deactivate, login-block only this pass, cross-service enforcement is a follow-on (design.md decision 5)
- [x] 1.4 Decide role boundaries — admin can remove/demote another admin; last-admin protection required (design.md decision 6)
- [x] 1.5 Decide which company fields are admin-editable vs. superuser-only — all fields, including `is_ngo`/`is_donor`, are admin-editable (design.md decision 7)
- [x] 1.6 Decide the `superuser-tenant-administration` mechanism — impersonation + reuse of `company-user-administration` endpoints for invite/remove/promote-demote/update-company; a dedicated superuser-scoped endpoint only for company deactivation (design.md decision 2)
- [ ] 1.7 Create the `donor-grantee-relationship` delta spec (new requirement: reject `donor_id == grantee_id`) via `/opsx:continue` — surfaced by decision 7, not yet a file under this change
- [ ] 1.8 PR merged (docs-only: design.md + spec updates)

## 2. Backend: company-user-administration — depends on 1

- [ ] 2.1 Add admin-scoped invite endpoint + accept-invite endpoint in `services/users/app/api/user_routes.py`, reusing `email_verification_token_hash`/`email_verification_expires_at`
- [ ] 2.2 Add admin-scoped user-removal endpoint (distinct from the existing self-service `DELETE /users/{user_id}`), scoped to the admin's own `customer_id`, reusing the GDPR soft-delete path, rejecting removal that would leave zero admins
- [ ] 2.3 Add admin-scoped role-update endpoint (promote/demote between `admin`/`user` within the admin's own company), rejecting a demotion that would leave zero admins, rejecting any attempt to set `role: superuser`
- [ ] 2.4 Add company-update endpoint in `services/users/app/api/customer_routes.py`, scoped to the admin's own `customer_id`, covering `name`/`country`/`currency`/`is_ngo`/`is_donor`
- [ ] 2.5 Add guard in `services/users/app/crud/donor_grantee_crud.py` rejecting `donor_id == grantee_id`
- [ ] 2.6 Tests: admin can invite/remove/promote/demote users and update company details (including `is_ngo`/`is_donor`) within their own `customer_id`; cannot act on another company's users/details; non-admin roles are rejected; last-admin protection holds; self-referential donor-grantee is rejected
- [ ] 2.7 Run users-service test suite and flake8 (`--max-line-length=100`) clean; PR merged

## 3. Frontend: Company Management page (admin) — depends on 2

- [ ] 3.1 Add an admin-only "Company Management" page listing the company's users, with invite, remove, and promote/demote actions
- [ ] 3.2 Add a form to update the company's own editable details, including `is_ngo`/`is_donor`
- [ ] 3.3 Tests: page and actions are hidden/inaccessible for non-admin roles
- [ ] 3.4 Run frontend test suite and lint clean; PR merged

## 4. Superuser tenant administration — depends on 1, 2, 3

- [ ] 4.1 Frontend: add a superuser-only company picker that starts an impersonation session (`POST /auth/impersonate`) and routes into the existing Company Management page from group 3 — no new backend endpoints needed for invite/remove/promote-demote/update-company
- [ ] 4.2 Add company-deactivate endpoint in `services/users/app/api/customer_routes.py`, gated on `role == "superuser" or is_impersonating`, setting the deactivation flag/timestamp on `CustomerModel` and blocking login/token-issuance for that company's users
- [ ] 4.3 Tests: superuser can act on any company's users/details via impersonation; a plain admin cannot deactivate their own company; superuser can deactivate directly or while impersonating; deactivated company's users cannot log in; non-superuser roles are rejected on deactivate
- [ ] 4.4 Run affected services' test suites, flake8 (`--max-line-length=100`), and frontend lint clean; PR merged
