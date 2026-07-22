## Context

`services/users` currently issues a `UserStatus.pending` account and a JWT on `POST /register`, and the frontend routes straight to `/onboarding` (`Register.tsx:29`). Nothing confirms the registrant controls the email address. There is no email-sending code anywhere in the repo — this is the first time we're wiring in a transactional email provider. There is, however, already a Celery worker (`services/worker`, RabbitMQ broker + Redis backend) with an unused `tasks.users.*` queue placeholder, and an existing pattern in `auth_routes.py` for merging boolean flags (`is_ngo`, `is_donor`) into JWT claims (added in #135/#136) that this change extends with `email_verified`.

This repo has hit JWT-staleness issues before (see the "stale auth flags after silent refresh" work folded into the donor-dashboard change): a boolean baked into a JWT at issuance can go stale the moment backend state changes. Email verification has exactly that shape — a user verifies, but their existing token still says `email_verified: false` until it's refreshed.

## Goals / Non-Goals

**Goals:**
- Send a confirmation email via Mailtrap when a user registers, without blocking the registration request.
- Verify a single-use, expiring token and flip the account to a verified state.
- Gate onboarding (not login) behind that verified state.
- Reuse existing infra: the Celery worker for async send, the existing JWT-claims-merging pattern for the new flag.
- Don't lock out users who registered before this change shipped.

**Non-Goals:**
- General-purpose transactional email templating/marketing email system — this is scoped to the verification flow only; the Mailtrap client can be reused later but we're not building a template engine now.
- Blocking login for unverified users (only onboarding/full-app access is gated) — see Open Questions.
- Phone/SMS verification, magic-link passwordless login — out of scope.

## Decisions

**Mailtrap product: Sending API (HTTPS), not SMTP.**
The worker calls Mailtrap's HTTP Sending API instead of relaying over SMTP. Rationale: one HTTPS client with an API token is simpler to configure and secret-manage across dev/staging/prod than SMTP host/port/TLS credentials, and it gives us delivery status in the response instead of a fire-and-forget SMTP handoff. Alternative considered: SMTP relay — rejected, no material benefit here and more config surface.

**Environment-conditional Mailtrap target: Sandbox in dev/staging, Live Send in prod.**
Mailtrap's Sandbox API captures mail in a testing inbox instead of delivering it, which is what we want for local/dev/CI. Which one is used is driven by an env var (e.g. `MAILTRAP_MODE=sandbox|live`), not by application logic branching.

**Send asynchronously via the existing Celery worker.**
The registration endpoint enqueues a `tasks.users.send_verification_email` task on the already-provisioned `tasks.users` queue and returns immediately. Rationale: registration shouldn't fail or hang on a third-party API call; the queue placeholder already exists and is otherwise unused. Alternative considered: send inline in the request — rejected, couples request latency/availability to Mailtrap's.

**Store a hashed, expiring, single-use token directly on the `User` row.**
Add `email_verified: bool`, `email_verification_token_hash: str | None`, `email_verification_expires_at: datetime | None` to `services/users/app/models/user.py`. The raw token is only ever in the emailed URL, never persisted (same principle as password-reset tokens elsewhere) — the DB holds a hash for lookup/comparison. Expiry: 24 hours; a new registration or resend request overwrites any prior token (invalidating it). Alternative considered: a separate `email_verification_tokens` table for a full audit trail — rejected for now as unnecessary volume/complexity (YAGNI); the `budget_status_history` precedent (#138) was for auditing *state transitions that matter to end users*, this is an internal, ephemeral credential.

**Backfill existing users as already-verified.**
The migration sets `email_verified = true` for every pre-existing row before the column becomes meaningfully enforced. Rationale: this change should only affect new signups, not silently lock out the existing user base.

**JWT gets an `email_verified` claim; verification success triggers a token refresh, not just a DB write.**
Following the existing `_role_flags`-style claims helper, `email_verified` is merged into the token payload at register/login/refresh (`auth_routes.py`). Because verifying an email doesn't happen in the same request as reading the JWT, the frontend must re-fetch/refresh the token immediately after a successful `POST /auth/verify-email` so the client's session claim matches DB state right away — reusing the silent-refresh mechanism already in the codebase rather than inventing a second one.

**Login remains ungated; only onboarding (and anything gated behind it) checks `email_verified`.**
An unverified user can still authenticate; the frontend route guard on `/onboarding` (and any post-onboarding app routes) redirects to a "confirm your email" screen instead. Rationale: locking out login entirely for a typo'd-but-real email creates a support burden with no verification path (can't resend if you can't reach the account state). See Open Questions for the alternative.

## Risks / Trade-offs

- **[Risk] Celery worker outage silently drops the verification email.** → Mitigation: Celery task-level retry with backoff on the Mailtrap call; `resend-verification` endpoint lets the user self-serve after the fact regardless of what happened to the first attempt.
- **[Risk] Mailtrap rate limits or transient API failures.** → Mitigation: same retry/backoff as above; failures logged so they show up in the existing Grafana Cloud observability pipeline rather than disappearing silently.
- **[Risk] Verification link is a bearer credential — if leaked (referrer headers, logs) it grants email confirmation.** → Mitigation: token is single-use (cleared on success) and short-lived (24h); only its hash is stored; the link is only ever sent to the registrant's inbox.
- **[Risk] Backfill mismarks an account that was never legitimately verified.** → Accepted trade-off: pre-existing accounts already had implicit trust (they've been operating in `pending`/`active` status without email confirmation); this change is about new signups going forward, not retroactively re-vetting the existing base.
- **[Risk] Stale JWT after verification (repeat of the earlier silent-refresh issue).** → Mitigation: explicit refresh call wired into the verify-email frontend flow, per the Decisions section above.

## Open Questions

- Should unverified users be blocked from logging in at all (stricter), rather than just gated at onboarding? Current design favors the softer gate for support/recoverability reasons — revisit if abuse patterns emerge.
- Do we want a rate limit specifically on `POST /auth/resend-verification` (e.g. 1/minute per account) to prevent it being used to spam an inbox? Leaning yes, deferring the exact limit to implementation.
