## 1. Data model & migration

- [ ] 1.1 Add `email_verified` (bool, default false), `email_verification_token_hash` (nullable str), `email_verification_expires_at` (nullable datetime) to `services/users/app/models/user.py`
- [ ] 1.2 Update `shared/schemas/user_schema.py` (and any user response schemas) to expose `email_verified`
- [ ] 1.3 Write Alembic migration adding the new columns, with a data migration step that sets `email_verified = true` for all pre-existing rows
- [ ] 1.4 Apply migration locally and confirm existing seeded/test users come back as verified

## 2. Mailtrap client & async send

- [ ] 2.1 Add `MAILTRAP_API_TOKEN`, `MAILTRAP_MODE` (sandbox|live), and sender address to service env config (do not commit real token values)
- [ ] 2.2 Build a small Mailtrap HTTP client wrapper (sending API) shared by the users service and worker
- [ ] 2.3 Add `tasks.users.send_verification_email` Celery task in `services/worker`, wired to the existing `tasks.users` queue, with retry/backoff on failure
- [ ] 2.4 Add a verification email template (subject/body with the verification link)

## 3. Users service endpoints

- [ ] 3.1 Update `POST /register` (`services/users/app/api/auth_routes.py`) to generate a hashed token + expiry, persist it, and enqueue the send-verification task instead of blocking on delivery
- [ ] 3.2 Add `POST /auth/verify-email` — validate token match + expiry, set `email_verified = true`, clear the stored token
- [ ] 3.3 Add `POST /auth/resend-verification` — no-op for already-verified accounts; otherwise regenerate token/expiry and enqueue a new send, invalidating the prior token
- [ ] 3.4 Extend the existing claims-merging helper alongside `is_ngo`/`is_donor` to include `email_verified` at register/login/refresh
- [ ] 3.5 Add/extend CRUD helpers in `services/users/app/crud/user_crud.py` for token generation, lookup-by-hash, and clearing

## 4. Frontend

- [ ] 4.1 Add a "check your email" screen shown immediately after registration instead of routing straight to `/onboarding`
- [ ] 4.2 Add a `/verify-email` route/page that reads the token from the URL, calls the verify endpoint, and on success triggers a token refresh so the client's `email_verified` claim is current
- [ ] 4.3 Add a resend-confirmation action (calls `POST /auth/resend-verification`) with basic rate-limit-aware UX (disable button after send)
- [ ] 4.4 Add a route guard on `/onboarding` (and any app routes gated behind it) that redirects users with `email_verified: false` to the confirm-email screen
- [ ] 4.5 Update `Register.tsx`/`Login.tsx` post-auth redirect logic to route unverified users to the confirm-email screen instead of onboarding

## 5. Tests

- [ ] 5.1 Backend: registration enqueues the send task and stores a hashed token (mock/assert on the Celery task call, not a real Mailtrap send)
- [ ] 5.2 Backend: verify-email endpoint — valid token, expired token, already-used token cases
- [ ] 5.3 Backend: resend-verification — unverified vs already-verified account behavior
- [ ] 5.4 Backend: JWT claims include `email_verified` and reflect DB state at register/login/refresh
- [ ] 5.5 Backend: migration backfill sets existing users to `email_verified = true`
- [ ] 5.6 Frontend: unverified user is redirected away from onboarding; verified user is not
- [ ] 5.7 Frontend: verify-email page success/failure states, including the post-verify token refresh

## 6. Docs

- [ ] 6.1 Document the new env vars (`MAILTRAP_API_TOKEN`, `MAILTRAP_MODE`, sender address) in the relevant service README/deployment docs
- [ ] 6.2 Note the onboarding-gate behavior change in user-facing/API docs if any exist for the registration flow
