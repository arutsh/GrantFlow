## Context

`services/users` currently has no admin-facing user/company management: `user_routes.py` only supports self-service create/update/delete (`DELETE /users/{user_id}` is the account owner deleting themselves, gated via `get_validated_user`, not an admin removing someone else). `customer_routes.py` only supports create/list/get — no update or delete. The `company-onboarding` spec already flags self-service invitation as a known, tracked gap.

Separately, `superuser-cross-tenant-access` shipped and archived (2026-08-17) as `customer-impersonation` + `privileged-access-audit`, before this change reached implementation. Its `/auth/impersonate` endpoint (`services/users/app/api/auth_routes.py:407-445`) mints a short-lived token carrying the superuser's own real `user_id`, the target `customer_id`, `role: "admin"`, and `is_impersonating: true` — i.e. a superuser who impersonates a company already holds an admin-equivalent token for that company. That is the load-bearing fact behind most of the decisions below.

This proposal was originally scoped shallow ("no deep analysis, revisit later"); this revision resolves every open question left from that pass, once `customer-impersonation` was confirmed shipped and its token shape confirmed by reading the code.

## Goals / Non-Goals

**Goals:**
- Capture the two actor-scoped capabilities (admin: own company; superuser: any company) as specs.
- Resolve the invite mechanism, deletion semantics, role boundaries, and field-scope questions concretely enough to implement.

**Non-Goals:**
- Deciding the invite email's copy/template content.
- Cross-service enforcement of company deactivation (`services/budget`, `services/reports` still trust already-issued JWTs) — tracked as a follow-on, not built here.
- An audit/action log for admin actions — deliberately deferred; see Risks/Trade-offs.
- Role-gating on who within a donor company can approve a grantee (`POST /donor-grantees/` is gated on `get_validated_user` only, no role check) — pre-existing gap, out of scope here.

## Decisions

### 1. Two capabilities, not one
`company-user-administration` (admin, own company) and `superuser-tenant-administration` (superuser, any company) are modeled separately because their authorization scope differs (`customer_id`-bound vs. unbound), even though the underlying operations (delete user, update company) overlap. This mirrors the existing pattern of separate capabilities per actor (e.g. `donor-dashboard` vs `grantee-dashboard-api`).

**Alternative considered**: a single capability with role-scoped requirements. Rejected to keep `superuser-tenant-administration`'s much smaller surface (see decision 2) separable from the admin spec.

### 2. Superuser acts through impersonation, not dedicated endpoints — except company deactivation
Invite, remove-user, promote/demote-user, and update-company need **no superuser-scoped backend code**. A superuser starts an impersonation session for the target company (`customer-impersonation`), receives a `role: "admin"` token scoped to that `customer_id`, and calls the exact same `company-user-administration` endpoints an admin would. `superuser-tenant-administration`'s backend surface shrinks to one action: **company deactivation**, which a plain admin must never be able to do to their own company. Since an impersonation token's `role` claim is `"admin"`, a naive `role == "superuser"` check would reject a legitimately-impersonating superuser, and a `role == "admin"` check would let real admins deactivate themselves. The deactivate endpoint therefore checks:

```python
is_superuser_acting = payload["role"] == "superuser" or payload.get("is_impersonating") is True
```

This is safe because only a superuser can ever mint a token with `is_impersonating: true` (enforced in `/auth/impersonate` itself).

**Alternative considered**: dedicated superuser-scoped endpoints mirroring the admin ones. Rejected — pure duplication of what impersonation already provides, for three of the four actions.

### 3. Invite mechanism
Inviting a user creates a `UserModel` row immediately: `customer_id` set to the inviter's, `status = pending`, `hashed_password = null`, visible in the company's user list right away as pending. Reuses the existing `email_verification_token_hash`/`email_verification_expires_at` columns and hashing helpers (`services/users/app/crud/user_crud.py`), but through a **new accept-invite endpoint** — distinct from `mark_email_verified` — that sets `hashed_password` (from the invitee's chosen password) and `email_verified = true` in one step, then clears the token. No new table; no password-reset flow exists to reuse instead (there isn't one in this codebase).

### 4. User removal reuses GDPR soft-delete
Admin-initiated user removal reuses the erasure path already built for self-service GDPR deletion (`data-subject-rights`): `deletion_requested_at`/`deleted_at` set, name/email tombstoned, active sessions revoked. Not a hard delete — avoids dangling `created_by`/`updated_by` references on budgets/reports the removed user authored, the same problem the GDPR path was built to solve.

### 5. Company deactivation, not deletion — cross-service enforcement is a follow-on
Company "delete" is soft-delete/deactivate: a new flag/timestamp on `CustomerModel`, not a hard delete or cascading cleanup. In this change's scope, deactivation blocks **login/token-issuance** for that company's users. It does **not** reach into `services/budget`/`services/reports` — those are separate databases that trust JWT claims and never call back to `services/users` to check customer status, so a deactivated company's user holding an already-issued, unexpired token can still write budgets/reports until it naturally expires. Closing that gap (a users-service callback, a shorter token TTL, or a claim-based check in each service) is tracked as a follow-on, not built here.

### 6. Role boundaries
An admin can remove or demote another admin of the same company (covers offboarding a co-founder), but any removal or demotion that would leave the company with zero admins is rejected — a "last admin" check on the write path.

### 7. Company field scope: fully admin-editable, including is_ngo/is_donor
`name`, `country`, `currency`, `is_ngo`, and `is_donor` are all admin-editable, including on the admin's own company. Framing: a company self-classifies as grantee-only, donor-only, or both — a business choice, not something requiring superuser gatekeeping.

This reopens a real risk flagged during review: `is_donor = true` lets a company unilaterally approve itself as a funder for *any* NGO customer (`donor-grantee-relationship`'s create requirement has no grantee-side consent step). Accepted as within the product's threat model for now — but it also makes a previously-unreachable case reachable: a company that is simultaneously `is_ngo` and `is_donor` (now a legitimate self-service combination) could create a `donor_grantees` record with `donor_id == grantee_id`, since `create_donor_grantee` (`services/users/app/crud/donor_grantee_crud.py:12`) has no guard against it today. **New requirement added to this change's scope**: reject `donor_id == grantee_id`. This needs a `donor-grantee-relationship` delta spec, not yet created under this change — create via `/opsx:continue`.

## Risks / Trade-offs

- **[Risk]** Company deactivation doesn't reach other services — an already-issued token from a deactivated company keeps working in budgets/reports until it expires. → **Mitigation**: accepted for this pass (decision 5); tracked as a follow-on.
- **[Risk]** `is_donor` self-service grants unilateral funder-approval power with no grantee consent. → **Mitigation**: accepted as within threat model (decision 7); the one concrete gap this surfaces (self-referential donor==grantee) is closed in this change.
- **[Risk]** No audit trail for admin actions (invite/remove/promote-demote/update-company/deactivate) beyond `created_by`/`updated_by` on the affected row (no before/after history, nothing recorded for removals). → **Mitigation**: deliberately deferred — this mirrors an identical, already-backlogged need for budget status history (GitHub #138); building one reusable audit-log pattern for both, once picked up, is preferred over two bespoke ones. Not built in this change.
