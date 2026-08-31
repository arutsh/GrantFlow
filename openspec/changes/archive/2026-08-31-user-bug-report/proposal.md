## Why

Pilot users are nonprofit grant managers, not developers — they won't file GitHub issues, so bugs go unreported and the team has no real-time visibility into pilot friction. A low-friction in-app "Report a problem" widget (mockup already built) closes that gap, but only if submissions actually reach the team immediately rather than sitting in a database no one checks.

## What Changes

- Add the "Report a problem" widget to the frontend: a floating trigger button plus a modal capturing free text, auto-captured context (page, browser, timestamp), and an optional screenshot attachment (per the existing mockup).
- Add a backend endpoint (in `services/users`, the existing cross-cutting/tenant-agnostic service) that accepts the report, uploads an optional screenshot to S3 via the existing `StorageService` abstraction, and persists a `bug_reports` record.
- Add an async Celery worker task that dispatches a notification after a report is saved, so the request returns immediately and delivery failures retry independently (mirrors the existing password-reset-email task pattern).
- Add a provider-agnostic **outbound notification** interface, mirroring the existing `EmailClient` abstraction in `shared/services/email_provider.py`, with a Slack Incoming Webhook as the first implementation. The submission flow and the Celery task depend only on the interface, not on Slack — swapping to email or another channel later is a new provider class plus a config change, no changes to the capture flow.
- Slack delivery uses an Incoming Webhook (works on the free plan) rather than a bot token; since a webhook can't upload files, the screenshot is delivered as a presigned S3 link in the message rather than an attached image.
- Wire the new route through all three gateway configs (`nginx/nginx-dev.conf`, `nginx/nginx.conf`, `Caddyfile`).

## Capabilities

### New Capabilities
- `bug-report-submission`: capturing a free-text bug report with auto-captured context (page, browser, timestamp) and an optional screenshot, persisting it server-side, and uploading the screenshot to object storage.
- `outbound-notifications`: a provider-agnostic interface for dispatching an event to an external channel, decoupled from what triggers it. Slack (Incoming Webhook) is the first provider; future providers (email, Teams, etc.) implement the same interface.

### Modified Capabilities
_None._ This reuses the existing `cloud-agnostic-storage` capability's `StorageService` as-is (no requirement changes) and does not touch `transactional-email`.

## Impact

- **`services/users`**: new `BugReportModel` + Alembic migration, new API route, new storage-client wiring (reusing `shared/storage/s3_storage_service.py`), extension of the existing `app/services/celery_client.py` producer.
- **`services/worker`**: new task module under `tasks/feedback/`, registration in `celery_app.py`'s `include=[]` list and `task_routes` (guarded by the existing `test_celery_task_registration.py`).
- **`shared/services`**: new `notification_provider.py` abstraction (interface + `NotificationError`) and a `slack_webhook_client.py` implementation, following the existing `email_provider.py`/`mailjet_client.py` pattern.
- **`frontend-typescript`**: new widget component + API call, added to the app shell so it's available on every page.
- **Gateway config**: `nginx/nginx-dev.conf`, `nginx/nginx.conf`, `Caddyfile` — new route for the bug-report endpoint.
- **New env var**: `SLACK_WEBHOOK_URL` (worker config, default `""`, following the existing secrets convention).
