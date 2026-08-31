## Context

The pilot's "Report a problem" widget (mockup already built) needs a backend that (1) stores every report as the durable record, (2) optionally stores a screenshot, and (3) notifies the team in near-real-time. The team currently uses a free Slack plan, which blocks Incoming-Webhook-only channels from receiving file uploads (that needs a bot token/OAuth app), and the requirement is explicit that Slack must not be hard-wired in — a future switch to email or another channel should not touch the submission flow.

The codebase already has two directly reusable patterns: `shared/services/email_provider.py`'s abstract `EmailClient` (provider-agnostic sender, concrete Mailjet/Mailersend/console implementations), and `shared/storage/s3_storage_service.py`'s `StorageService` (already used by budget-report attachments). This design reuses both rather than inventing new ones.

## Goals / Non-Goals

**Goals:**
- Persist every submitted report in `services/users` regardless of whether notification delivery succeeds.
- Dispatch a notification through a provider-agnostic interface; Slack (Incoming Webhook) is the only implementation now, but the submission flow and the Celery task depend only on the interface.
- Keep screenshot upload within the existing storage abstraction and validation conventions (content-type sniffing, size cap) already used for budget-report attachments.
- Keep delivery async (Celery) so a slow/failing notification never blocks or fails the user's submission.

**Non-Goals:**
- No two-way sync (Slack thread replies updating report status in-app) — v1 is fire-and-forget notify.
- No Slack bot/OAuth app or in-message file upload — free-plan Incoming Webhook only; screenshots ship as a link.
- No triage/inbox UI in GrandFlow itself — Slack (and the DB table, queryable directly) is the triage surface for the pilot.
- No new microservice — this is one table, one endpoint, one task, sized like the existing attachment feature.

## Decisions

**1. Provider-agnostic `NotificationProvider` interface, not a direct Slack call.**
New `shared/services/notification_provider.py`: an abstract `NotificationProvider` with `send(message: NotificationMessage) -> None`, and `NotificationMessage` as a plain dataclass (`title`, `body`, `fields: list[tuple[str, str]]`, `link: str | None`) — channel-neutral, no Slack-specific shape. `shared/services/slack_webhook_client.py` implements it for Slack. The Celery task and the submission flow both depend only on the interface. Mirrors `EmailClient`/`EmailProviderError` exactly. Alternative considered: call Slack's webhook directly from the task — rejected, since it's the one thing the user explicitly asked to keep swappable.

**2. Screenshot ships as a presigned link, not an inline upload.**
A free-plan Incoming Webhook can only post text/Block-Kit JSON, not files. The screenshot is uploaded to S3 via the existing `StorageService.save()` (same as budget attachments), and the Slack message includes a presigned `GET` URL. Alternative considered: Slack bot token + `files.upload` — gives real inline images but requires installing an OAuth app on the workspace; deferred, and made easy to add later since it's just a second `NotificationProvider`-conformant client, not a rework of the capture flow.

**3. Presigned link needs a longer expiry than the existing default.**
`S3StorageService.presigned_download_url()` defaults to `expires_in=300` (5 minutes) — fine for an immediate in-app download, wrong for a Slack message someone might open hours later. The bug-report notification path calls it with an explicit longer expiry (24h) so the link in Slack is still valid when read.

**4. Async dispatch via a new Celery task, not a synchronous call in the endpoint.**
New task `tasks.feedback.post_notification` in `services/worker/tasks/feedback/`, following the `send_password_reset_email` pattern (`bind=True`, retry with backoff on `NotificationError`). `services/users/app/services/celery_client.py` gets an `enqueue_bug_report_notification(...)` producer method calling `send_task(...)`. The task module must be added to `celery_app.py`'s `include=[]` and `task_routes`; `test_celery_task_registration.py` already fails CI if that's forgotten, so no new guard is needed.

**5. New `BugReportModel` in `services/users`, not a reuse of budget's `AttachmentModel`.**
Budget's `AttachmentModel` FKs tightly to `report_lines` and doesn't fit a standalone report. New table `bug_reports` (GUID PK, `AuditMixin`, submitter user id, free-text body, page/browser/timestamp context fields, nullable `screenshot_storage_key`), migrated in `services/users/migrations/versions/`. The endpoint and model live in `services/users` because it's the existing cross-cutting/tenant-agnostic service (auth, admin), not a domain service like budget/chat — the widget must work from any page regardless of which domain owns it.

**6. Local/dev fallback: no-op provider when `SLACK_WEBHOOK_URL` is unset.**
Mirrors `console_email_client.py` — a `ConsoleNotificationProvider` (or a guard inside the Slack client) logs instead of calling out when the webhook URL is blank, so local dev and tests don't need a real webhook configured.

**7. Screenshot validation mirrors budget's attachment service, tightened for this use case.**
Reuse the content-type allowlist + magic-byte sniff from `attachment_services.py`, restricted to image types only (`png`, `jpg`, `webp`) with a 5MB cap (screenshots, not arbitrary files).

## Risks / Trade-offs

- **[Risk]** `SLACK_WEBHOOK_URL` leaking would let anyone post arbitrary messages into the team's channel. → **Mitigation**: it's worker-only config, never sent to the frontend; treat it as a secret in `.env.worker.*` per existing env-file handling (flag before any commit that touches those files).
- **[Risk]** A screenshot can capture sensitive nonprofit financial data visible on-screen at the time. → **Mitigation**: flagged as an open question below rather than silently shipped; likely needs a short in-widget note, not a technical control.
- **[Risk]** Slack's free plan only retains 90 days of channel history — Slack must not become the system of record. → **Mitigation**: the `bug_reports` table is the durable record; Slack is purely the real-time alert.
- **[Risk]** A burst of submissions (accidental double-click, or pilot users retrying after a perceived failure) could flood the Slack channel — the same failure mode that got Mailjet auto-blocked from a pentest flood previously. → **Mitigation**: out of scope for v1 given small pilot size; flagged as an open question to revisit if it happens.
- **[Risk]** Forgetting to add the new task module to `celery_app.py`'s `include=[]` silently drops all notifications. → **Mitigation**: already covered by the existing `test_celery_task_registration.py` CI guard.

## Migration Plan

1. `shared/services/notification_provider.py` + `slack_webhook_client.py` (pure code, no migration).
2. `services/users`: `BugReportModel` + Alembic migration for `bug_reports`.
3. `services/worker`: `tasks/feedback/post_notification.py`, register in `celery_app.py`, add `SLACK_WEBHOOK_URL` (default `""`) to worker config and `.env.worker.{dev,local,prod}` — user to fill in the real webhook URL out of band.
4. `services/users`: endpoint + `celery_client.py` producer method + storage-client wiring.
5. Gateway: add the route to `nginx-dev.conf`, `nginx.conf`, and `Caddyfile`.
6. Frontend: wire the existing widget mockup to the new endpoint.

Fully additive (new table, new route, new task) — rollback is reverting the change; no existing data or endpoints are touched.

## Open Questions

- Does the widget need a warning about not capturing sensitive on-screen data before a screenshot is taken/attached?
- Is any submission rate limit or de-dupe needed for v1, given the small pilot cohort, or is that premature?
- If Slack's free-plan limits become a real constraint later, is the next step a paid plan/bot token (inline images) or moving to a different channel entirely (email)? No decision needed now — the interface from Decision 1 is what keeps that option open.
