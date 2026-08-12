## Why

MailerSend's trial account caps unique recipients, which is already blocking local/dev testing of the email-verification flow (a real registration silently failed to deliver because of this cap). Rather than hard-swapping to Mailjet and repeating the same single-vendor lock-in, decouple email sending from any one provider so the active provider is a config decision, not a code change — Mailjet becomes available now, MailerSend stays fully intact, and the choice is switchable per environment via an env var.

## What Changes

- Introduce a provider-agnostic transactional-email interface in `shared/services/` that both providers implement, so call sites depend on the interface, not a vendor SDK/payload shape.
- Add a `MailjetClient` implementing that interface, alongside the existing `MailerSendClient` — **MailerSend is not removed**.
- Add an `EMAIL_PROVIDER` env var (`mailersend` | `mailjet`) that selects which client the worker instantiates at runtime; default stays `mailersend` so no environment changes behavior unless explicitly reconfigured.
- Normalize provider-specific payload construction (template id, personalization/variable keys, auth scheme) behind the interface — `send_verification_email.py` calls one method and stays provider-agnostic.
- Add Mailjet config: `MAILJET_API_KEY`, `MAILJET_SECRET_KEY` (Mailjet uses key+secret Basic Auth, not a bearer token), `MAILJET_SENDER_EMAIL`, `MAILJET_SENDER_NAME`, `MAILJET_VERIFICATION_TEMPLATE_ID`, `MAILJET_API_URL`.
- Recreate the verification template in Mailjet's dashboard so it's usable once `EMAIL_PROVIDER=mailjet` is set anywhere.

## Capabilities

### New Capabilities
- `transactional-email`: provider-agnostic capability for sending transactional emails (starting with the verification email use case), with the active provider selected at runtime via `EMAIL_PROVIDER`, and MailerSend + Mailjet as the initial pluggable implementations.

### Modified Capabilities
- none. The existing (unarchived) `email-verification` spec's behavior — enqueue-and-send-async, single-use expiring token, resend endpoint — is unchanged; only *which vendor* fulfills the send is now a runtime choice, which is implementation detail owned by the new `transactional-email` capability rather than a requirement change on verification itself.

## Impact

- `shared/services/`: new provider interface (e.g. `email_client.py` protocol/ABC) + new `mailjet_client.py`; existing `mailersend_client.py` untouched.
- `services/worker/tasks/users/send_verification_email.py`: switches from constructing `MailerSendClient` directly to resolving a client via the interface based on `EMAIL_PROVIDER`.
- `services/worker/config.py`: add `EMAIL_PROVIDER` + `MAILJET_*` settings alongside existing `MAILERSEND_*` settings.
- `services/worker/.env.worker.{dev,local,prod}`: add Mailjet vars; `.env.worker.dev`/`.env.worker.local` likely flip `EMAIL_PROVIDER=mailjet` first to unblock dev testing, prod stays on `mailersend` until Mailjet is validated.
- `docker-compose.local.yml`, `.github/workflows/deploy.yml` (secrets passthrough), `docs/deployment/DEPLOYMENT_MODES.md`: extended, not replaced.
- No changes to `services/users` or the frontend — the Celery-task boundary (`enqueue_verification_email`) already isolates them from provider details.
- No test rewrites required for existing tests (none reference MailerSend directly); new tests should cover the provider-selection logic and the Mailjet client, since none existed for the MailerSend client either.
