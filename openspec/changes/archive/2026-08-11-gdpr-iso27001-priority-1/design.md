## Context

This is priority 1 of a two-part compliance program (see `gdpr-iso27001-priority-2` for the operational/infra half). It targets the gaps that are both legally load-bearing under GDPR and externally checkable — a user testing account deletion, or a donor's technical diligence probing session/password handling. Touches `services/users`, `shared/security`, and the frontend auth flow, so a design pass is needed before task breakdown to get the shared mechanisms (session revocation, consent state) right the first time.

## Goals / Non-Goals

**Goals:**
- Give users a working right to erasure, access, and rectification.
- Make sessions revocable and passwords enforceable — currently the two highest-severity access-control gaps.
- Produce documentation (`SECURITY.md`, subprocessor list) concrete enough to link to when the team makes any public compliance claim.
- Extend existing patterns (`AuditMixin`, per-service FastAPI routers, `shared/security`) rather than introducing new frameworks.

**Non-Goals:**
- Retention limits on stored chat/audit content, backups, internal TLS, or CI dependency scanning — tracked in `gdpr-iso27001-priority-2`.
- Formal ISO 27001 certification or legal review/sign-off of the privacy policy stub.
- Full field-level encryption-at-rest for all PII (flagged as a residual risk, not solved here).

## Decisions

**1. Consent and deletion state live on `UserModel`, not a separate table.**
Add `consent_data_processing_at`, `consent_marketing_at` (nullable timestamps — presence = granted, null = not granted/withdrawn) and `deletion_requested_at`/`deleted_at` to `services/users/app/models/user.py`. Alternative considered: a separate `ConsentRecord` table for full history. Rejected for v1 — current/last-known consent state is what's needed for the app to function; a full consent-change audit trail can reuse `AuditMixin` later if required.

**2. Erasure is soft-delete + anonymization, not hard delete.**
`DELETE /users/{id}` sets `deleted_at`, scrubs `first_name`/`last_name`/`email` to a tombstone value, invalidates all sessions, and keeps the row (financial records via `created_by`/`updated_by` foreign keys must not dangle — budget/report data is the nonprofit's institutional record, not solely the user's personal data, so it survives with an anonymized actor reference). Hard-delete was rejected because it would either cascade-delete financial records or leave orphaned foreign keys.

**3. Session revocation via a `revoked` check on every authenticated request, not a separate blocklist cache.**
`SessionModel.revoked` already exists but is unused. Wire `get_current_user` (`shared/security/dependencies.py`) to check the session's `revoked` flag via a lookup keyed by a new `sid` claim embedded in the JWT. Alternative considered: Redis-backed token blocklist for O(1) revocation checks. Rejected for now — traffic is low enough that a DB lookup per request (already happening for `get_current_user`) isn't a bottleneck, and it avoids adding Redis as a hard dependency for security-critical logic. Also shorten access-token TTL from 5 days to 15–30 minutes with refresh-token-driven renewal, since long-lived unrevocable-by-default tokens were the actual risk. There are no production users yet, so this ships directly rather than behind a phased rollout — the TTL stays env-configurable for ops flexibility, not as a rollback safety net.

**4. Password policy enforced via a shared Pydantic validator, reused by both registration and password-change.**
Add `validate_password_strength` in `shared/security/` (min length, not-all-numeric, not equal to email/name), called from `RegisterRequest` and any password-change schema. Login rate-limiting reuses the existing pattern from `services/ai/app/services/rate_limiter.py` rather than inventing a new mechanism. No grandfathering of pre-policy passwords — with no production users, there's nothing to grandfather, so the policy simply applies to every registration and password change from day one.

**5. Security documentation is written, not generated.**
`SECURITY.md` and the subprocessor list are hand-authored markdown, reviewed like any other PR. No tooling decision needed here — the risk is content accuracy (listing every subprocessor and its actual data flow), not implementation.

## Risks / Trade-offs

- [Anonymizing users on erasure still leaves their financial actions (budgets, reports) attributable via `created_by` UUID, which is arguably still personal data if the org is small enough to re-identify] → Mitigation: document this as an accepted residual-processing basis (legitimate interest / legal-obligation for financial record-keeping) in the privacy policy, not a code fix.
- [Session-revocation check adds a DB read to the hot auth-dependency path] → Mitigation: index `SessionModel` on the `sid` claim value; acceptable at current traffic, revisit with a cache if it becomes a bottleneck.
- [Shortening access tokens to 15–30 min requires the frontend to implement silent refresh or users get logged out mid-session] → Mitigation: no production users yet means no live sessions to break during rollout, but the frontend work (silent refresh) still has to land in the same PR as the backend TTL change, not after it (memory shows groundwork already exists from the donor-dashboard work — `[[project_stale_auth_flags_silent_refresh]]`).
- [Publishing a subprocessor list before priority 2's internal-TLS and backup work lands could read as overclaiming maturity] → Mitigation: the doc explicitly scopes itself to "subprocessors and their data flows," not a blanket compliance claim; frame remaining hardening as in-progress.

## Migration Plan

No production users exist yet, so this ships as a direct cutover rather than a phased rollout — there's no live traffic or existing accounts to protect during deploy.

1. Ship DB migrations (consent fields, deletion fields, `sid` session claim support) additively — nullable columns, no backfill required.
2. Land session-revocation and the shortened access-token TTL together with the frontend silent-refresh change, in the same PR, so there's never a deployed state where the backend expects refresh behavior the frontend doesn't have yet.
3. Password policy applies immediately to all registrations and password changes.
4. Rollback: all schema changes are additive; the token-TTL value stays env-configurable for ops convenience, not as a required rollback mechanism.

## Open Questions

- Should data export be synchronous (small orgs) or async/email-delivered (larger orgs with many budget/report records)?
- Does the public compliance-claim wording wait for priority 2 as well, or is priority 1 alone considered sufficient to publish? (Recommend: revisit landing-page copy once this ships, decide then.)
