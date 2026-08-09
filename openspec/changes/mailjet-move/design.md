## Context

`shared/services/mailersend_client.py` is the only transactional-email code in the repo today: one class, one method (`send_template_email`), hardwired to MailerSend's HTTP Email API (Bearer-token auth, `template_id` + flat `personalization` dict). Its only caller is `services/worker/tasks/users/send_verification_email.py`, which builds a `MailerSendClient` directly from `MAILERSEND_*` settings in `services/worker/config.py`. There is exactly one email use case in the codebase (registration verification), so the blast radius of this change is small and fully contained in `services/worker` + `shared/services`.

The trigger: MailerSend's trial account caps unique recipients, and that cap was hit during real testing (a registration's verification email was silently rejected — see the 422 in worker logs). Rather than migrate to Mailjet outright, the ask is to make the provider swappable via config, add Mailjet as a second implementation, and leave MailerSend in place.

## Goals / Non-Goals

**Goals:**
- Define a provider-agnostic interface for sending a transactional email (recipient, subject, template id, personalization).
- Add a `MailjetClient` implementing that interface; keep `MailerSendClient` working and unmodified in behavior.
- Select the active provider at worker process start via an `EMAIL_PROVIDER` env var; default to `mailersend` so no existing environment changes behavior without explicit reconfiguration.
- Normalize the personalization data contract so the same call-site dict works for either provider without per-vendor branching at the call site.

**Non-Goals:**
- General-purpose email templating/marketing system — still scoped to the single verification-email use case.
- Automatic failover between providers (try Mailjet, fall back to MailerSend on failure) — single active provider only, revisit only if reliability data later justifies it.
- Hot-swapping providers without a restart — `EMAIL_PROVIDER` is read at process start like every other setting in this codebase.
- Fixing the pre-existing blind-retry-on-4xx gap (flagged separately) — out of scope, but the shared error type is shaped so that fix can land later without another refactor.

## Decisions

**Shared interface + shared error type in `shared/services/email_provider.py`.**
A `Protocol` (or ABC) `EmailProvider` with one method — `send_template_email(to_email, to_name, subject, template_id, personalization: dict) -> None` — matching the existing MailerSend client's shape almost exactly, since that shape is already close to provider-neutral. A single `EmailProviderError` becomes the base exception; `MailerSendError` and the new `MailjetError` both subclass it, so callers can catch one type. `EmailProviderError` gets optional `status_code: int | None` and `retryable: bool | None` fields now — both clients populate them — even though nothing consumes them yet, so the known retry-classification gap doesn't have to be rediscovered later. Alternative considered: separate per-provider call sites with an `if EMAIL_PROVIDER == ...` branch in the task itself — rejected, scatters the decision instead of centralizing it.

**Factory function picks the client, not scattered conditionals.**
`get_email_client()` (in the worker, next to the existing `_get_client()` it replaces) reads `settings.EMAIL_PROVIDER`, matches it against a small registry (`{"mailersend": MailerSendClient, "mailjet": MailjetClient}`), and instantiates the matching client from that provider's settings block. An unrecognized value raises immediately rather than silently defaulting — a misconfigured provider should fail loud, not fall back to whatever was previously wired.

**Personalization stays flat.**
MailerSend's `personalization` currently includes a nested `account: {name: ...}`. Mailjet's `Variables` are flat key-value pairs with no nested-object support. Decision: flatten `account.name` → `account_name` in the shared call-site dict (a one-line change in `send_verification_email.py`), and update the MailerSend dashboard template's variable reference to match. This keeps the interface's data contract flat and provider-agnostic instead of each client doing ad hoc flattening/unflattening.

**Mailjet auth is key+secret, not a bearer token.**
`MailjetClient.__init__` takes `api_key` and `secret_key` (HTTP Basic Auth per Mailjet's Send API v3.1), distinct from `MailerSendClient`'s single `api_token`. The shared interface doesn't expose auth at all — it's constructor-time configuration, invisible to callers — so this difference doesn't leak past the client boundary.

**Config default keeps prod behavior unchanged.**
`EMAIL_PROVIDER` defaults to `mailersend` in `services/worker/config.py`. Dev/local env files can flip it to `mailjet` once the Mailjet dashboard template exists, unblocking local testing immediately. Prod stays on `mailersend` until Mailjet is validated in dev — flipping prod is a separate, later decision, not part of this change's rollout.

## Risks / Trade-offs

- **[Risk] Two dashboard-hosted templates (MailerSend + Mailjet) can drift in copy/wording.** → Accepted; template content already lives outside the repo for MailerSend, this doesn't make that worse, just doubles it. No automation planned.
- **[Risk] Shared error type flattens provider-specific detail.** → Mitigated by adding `status_code`/`retryable` fields now, even unused, so the existing blind-retry gap isn't compounded by this change.
- **[Risk] New Mailjet client ships without unit tests, repeating how the MailerSend client shipped untested.** → `tasks.md` includes a unit-test task for both the new client and the provider-selection factory.
- **[Risk] `EMAIL_PROVIDER` typo in an env file silently reverts to MailerSend if the factory defaults on unknown values.** → Mitigated by the factory decision above: unknown values raise at startup, they don't fall back.

## Migration Plan

1. Add `shared/services/email_provider.py` (interface + `EmailProviderError`) — additive, no behavior change.
2. Refactor `MailerSendClient` to implement the interface and raise the shared error type (subclassed); verify existing verification-email flow is unaffected.
3. Add `MailjetClient` + `MAILJET_*` settings in `config.py` and all three worker env files.
4. Add `EMAIL_PROVIDER` setting (default `mailersend`) and the `get_email_client()` factory; wire it into `send_verification_email.py` in place of the current direct `MailerSendClient` construction.
5. Create the verification template in Mailjet's dashboard; flip `EMAIL_PROVIDER=mailjet` in `.env.worker.dev` / `.env.worker.local` to validate end-to-end.
6. Leave prod on `mailersend` (default); document the flip procedure in `docs/deployment/DEPLOYMENT_MODES.md` for when prod is ready to switch.

**Rollback:** unset or reset `EMAIL_PROVIDER` to `mailersend` — no data migration involved, fully reversible via config alone.

## Open Questions

- Should the shared error's `status_code`/`retryable` fields be wired into the Celery retry logic as part of this change, or stay unused until a dedicated follow-up? Leaning: leave unused here — populating them is nearly free while writing/refactoring both clients, but consuming them is a separate, already-identified fix.
- Is a Mailjet sandbox/test mode available equivalent to MailerSend's trial-domain cap, worth documenting in DEPLOYMENT_MODES.md alongside the existing MailerSend trial-domain note? To confirm during implementation.
