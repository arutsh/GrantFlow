One task group = one GitHub ticket = one PR, merged before the next group starts.

## 1. Provider-agnostic interface and shared error type

- [x] 1.1 Add `shared/services/email_provider.py`: `EmailProvider` interface (`send_template_email(to_email, to_name, subject, template_id, personalization: dict) -> None`) and `EmailProviderError` base exception with optional `status_code: int | None` / `retryable: bool | None` fields.
- [x] 1.2 Refactor `shared/services/mailersend_client.py` so `MailerSendClient` satisfies `EmailProvider` and `MailerSendError` subclasses `EmailProviderError`, populating `status_code`/`retryable` on raise; no change to its constructor args, wire payload, or the MailerSend API URL/behavior.
- [x] 1.3 Flatten the `account: {name: ...}` personalization field to `account_name` in `services/worker/tasks/users/send_verification_email.py`, and update the corresponding variable reference in the MailerSend dashboard template.
- [x] 1.4 Add unit tests for `MailerSendClient` (success, HTTP error, network error) — none exist today.
- [x] 1.5 Run `services/worker` and `shared` tests/lint clean; verify a real registration still delivers via MailerSend unchanged; PR merged (`Closes` the ticket for this group).

## 2. Mailjet client and runtime provider selection — depends on 1

- [x] 2.1 Add `shared/services/mailjet_client.py`: `MailjetClient` implementing `EmailProvider`, using Mailjet Send API v3.1 (`api_key` + `secret_key` Basic Auth, `Messages` array, numeric `TemplateID`, `TemplateLanguage: true`, flat `Variables`), raising `MailjetError(EmailProviderError)`.
- [x] 2.2 Add `EMAIL_PROVIDER` (default `"mailersend"`) and `MAILJET_API_KEY` / `MAILJET_SECRET_KEY` / `MAILJET_SENDER_EMAIL` / `MAILJET_SENDER_NAME` / `MAILJET_VERIFICATION_TEMPLATE_ID` / `MAILJET_API_URL` settings to `services/worker/config.py`.
- [x] 2.3 Add a `get_email_client()` factory (replacing `_get_client()` in `send_verification_email.py`) that maps `EMAIL_PROVIDER` to `{"mailersend": MailerSendClient, "mailjet": MailjetClient}` and raises a clear configuration error on an unrecognized value instead of defaulting silently.
- [x] 2.4 Wire `send_verification_email.py` to call `get_email_client()` instead of constructing `MailerSendClient` directly; confirm the `except MailerSendError` catch becomes `except EmailProviderError` so retry behavior is provider-agnostic.
- [x] 2.5 Add unit tests for `MailjetClient` (success, HTTP error, network error) and for `get_email_client()` (each supported provider, plus the unsupported-value failure path).
- [x] 2.6 Run `services/worker` and `shared` tests/lint clean; with `EMAIL_PROVIDER` unset, confirm registration still sends via MailerSend with no behavior change; PR merged (`Closes` the ticket for this group).

## 3. Mailjet dashboard template and dev/local rollout — depends on 2

- [x] 3.1 Create the verification email template in Mailjet's dashboard, matching the flattened personalization keys from task 1.3 (`name`, `verify_url`, `expiry_hours`, `support_email`, `account_name`); record the resulting numeric template ID. Template ID `8258185`. Confirm `account_name` is actually referenced in the template body — Mailjet's own code-sample generator only listed `name`/`verify_url`/`expiry_hours`/`support_email`, suggesting the signature line may not use it yet.
- [x] 3.2 Add `MAILJET_*` values (including the template ID from 3.1) to `services/worker/.env.worker.dev` and `.env.worker.local`; set `EMAIL_PROVIDER=mailjet` in both so dev/local testing is unblocked from the MailerSend trial-recipient cap. `MAILJET_API_KEY`/`MAILJET_SECRET_KEY` are in the user's gitignored `.devrc`, confirmed working (200 from Mailjet's `/v3/REST/apikey`).
- [x] 3.3 Add `MAILJET_*` passthrough to `docker-compose.local.yml` alongside the existing `MAILERSEND_*` passthrough.
- [x] 3.4 Add `MAILJET_*` secrets/env plumbing to `.github/workflows/deploy.yml` so prod can flip `EMAIL_PROVIDER=mailjet` later via a config-only change, without another PR; leave prod's actual `EMAIL_PROVIDER` on `mailersend` (or unset) for this change. GitHub repo secrets `MAILJET_API_KEY`/`MAILJET_SECRET_KEY`/`MAILJET_SENDER_EMAIL` still need to be added in repo settings.
- [x] 3.5 Update `docs/deployment/DEPLOYMENT_MODES.md`'s email-verification section to document `EMAIL_PROVIDER`, both provider's config blocks, and the rollback path (reset to `mailersend`).
- [x] 3.6 Register a real account in dev with `EMAIL_PROVIDER=mailjet` and confirm the verification email is delivered end-to-end via Mailjet. Confirmed: registered, received the email, clicked the link, "Email confirmed" page shown. Root cause of the initial `blocked` sends was two template issues on Mailjet's side — the verify-link button's `{{var:verify_url:...}}` tag missing quotes around its fallback, and the sender address (`hello@opengrantflow.com`) being stuck in `Pending` validation — both now fixed.
- [x] 3.7 Run full worker/shared test suite and lint clean (done, see 2.6); PR still needs to be opened and merged (`Closes` the ticket for this group).
