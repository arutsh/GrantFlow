## Context

`services/users` currently has no admin-facing user/company management: `user_routes.py` only supports self-service create/update/delete (`DELETE /users/{user_id}` is the account owner deleting themselves, gated via `get_validated_user`, not an admin removing someone else). `customer_routes.py` only supports create/list/get — no update or delete. The `company-onboarding` spec already flags self-service invitation as a known, tracked gap.

Separately, `superuser-cross-tenant-access` (in progress, not yet implemented) is building session-level impersonation: a superuser mints a token scoped to a target `customer_id`, then uses the existing app as that customer. That change's design explicitly removes role-based `if role == superuser: <unscoped>` bypasses in budget/report code in favor of `customer_id`-presence scoping — the same pattern would apply here.

This proposal was intentionally scoped shallow ("no deep analysis, revisit later") — the goal is a placeholder spec capturing the shape of the feature and the open questions, not a final architecture.

## Goals / Non-Goals

**Goals:**
- Capture the two actor-scoped capabilities (admin: own company; superuser: any company) as specs.
- Surface the relationship to `superuser-cross-tenant-access` as an explicit decision point rather than silently picking one.

**Non-Goals:**
- Deciding the invite-delivery mechanism (email template, token flow) in detail.
- Deciding whether superuser actions here are separate endpoints or routed through impersonation — left open.
- Building the page itself in this pass.

## Decisions

### 1. Two capabilities, not one
`company-user-administration` (admin, own company) and `superuser-tenant-administration` (superuser, any company) are modeled separately because their authorization scope differs (`customer_id`-bound vs. unbound), even though the underlying operations (delete user, update company) overlap. This mirrors the existing pattern of separate capabilities per actor (e.g. `donor-dashboard` vs `grantee-dashboard-api`).

**Alternative considered**: a single capability with role-scoped requirements. Rejected for now to keep the superuser question (see Open Questions) separable without reshaping the admin spec later.

## Risks / Trade-offs

- **[Risk]** Building superuser-scoped endpoints here that duplicate what impersonation (from `superuser-cross-tenant-access`) would give for free once shipped. → **Mitigation**: not resolved in this pass; flagged as the primary open question, to be decided before `superuser-tenant-administration` is implemented.
- **[Risk]** Company delete is destructive (orphans users, budgets, reports across services with no cross-service cascade — DB-per-service, per `superuser-cross-tenant-access`'s design.md). → **Mitigation**: left as an open question; likely needs soft-delete/deactivation semantics rather than a hard delete.

## Open Questions

- **Relation to `superuser-cross-tenant-access`**: should superuser delete/update-any-user and delete/update-any-company be their own superuser-scoped endpoints, or should the superuser instead mint an impersonation session (once that change ships) and use the same admin-scoped endpoints as `company-user-administration`? The latter would mean `superuser-tenant-administration` needs no new backend endpoints at all, only the frontend company picker plus reuse of admin endpoints — but blocks on impersonation shipping first. Revisit once `superuser-cross-tenant-access` lands or its timeline is clearer.
- **Invite mechanism**: does inviting a user create a `pending` `UserModel` row immediately (visible in company user lists before acceptance) or a separate invite-token table? Does it reuse the existing `email_verification_token_hash`/`transactional-email` machinery (`services/users/app/models/user.py`, `email-verification` capability) or need its own token type?
- **Deleting a user**: hard delete, or reuse the existing soft-delete/anonymization path already built for GDPR self-service erasure (`deletion_requested_at`/`deleted_at` on `UserModel`, `data-subject-rights` capability)? The latter seems consistent but isn't confirmed.
- **Deleting a company**: what happens to its users, budgets, and reports (other services, DB-per-service)? Hard delete, soft-delete/deactivate, or blocked while active users/budgets exist?
- **Role boundaries**: can an admin remove or demote another admin of the same company (including themselves), or only non-admin users? Is there always at least one admin required per company?
- **Company detail update scope**: which fields can an admin change (`name`, `country`, `currency`) vs. which are superuser-only (e.g. `is_ngo`/`is_donor`, since those affect donor-grantee eligibility per `donor-grantee-relationship`)?
