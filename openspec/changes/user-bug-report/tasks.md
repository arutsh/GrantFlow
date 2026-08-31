One task group = one GitHub ticket; in practice all four groups shipped together on a single branch/PR (`Closes #256, Closes #258, Closes #259`) rather than four sequential PRs — the per-group "run tests/lint clean; PR merged" tasks below are ticked against that one PR.

## 1. Outbound notification interface (shared)

- [x] 1.1 Add `shared/services/notification_provider.py`: abstract `NotificationProvider` (`send(message: NotificationMessage) -> None`) and `NotificationMessage` dataclass (`title`, `body`, `fields: list[tuple[str, str]]`, `link: str | None`), plus `NotificationError(message, status_code=None, retryable=None)` mirroring `EmailProviderError`.
- [x] 1.2 Add `shared/services/slack_webhook_client.py`: `SlackWebhookProvider` posting a Block-Kit-formatted message to a configured webhook URL via a reused `httpx.Client`, following `mailjet_client.py`'s retryable-vs-non-retryable error mapping (network errors and 5xx/429 → retryable; 4xx other than 429 → non-retryable).
- [x] 1.3 Add a `ConsoleNotificationProvider` (or an in-client guard) that logs instead of sending when no webhook URL is configured, mirroring `console_email_client.py`.
- [x] 1.4 Add a small provider-selection helper (env-driven, same shape as the email provider builder) so callers get a configured provider without knowing which implementation backs it.
- [x] 1.5 Unit tests: message formatting, retryable failure (network error, 500, 429), non-retryable failure (400, 404), and the no-webhook-configured fallback.
- [x] 1.6 Run `shared`'s test suite and lint clean; PR merged (`Closes #256`).

## 2. Bug report submission backend (services/users) — depends on 1

- [x] 2.1 Add `BugReportModel` (GUID PK, `AuditMixin`, submitter user id, description text, page path, browser/user-agent string, client timestamp, nullable `screenshot_storage_key`) and the Alembic migration in `services/users/migrations/versions/`.
- [x] 2.2 Add a `storage_client.py` singleton in `services/users/app/services/` wiring the existing `shared/storage/s3_storage_service.py` `S3StorageService` from `services/users` config (`STORAGE_ENDPOINT_URL`/`STORAGE_ACCESS_KEY`/`STORAGE_SECRET_KEY`/`STORAGE_BUCKET_NAME`).
- [x] 2.3 Add screenshot validation (content-type allowlist restricted to PNG/JPEG/WebP, magic-byte sniffing, 5MB size cap) adapted from `services/budget/app/services/attachment_services.py`.
- [x] 2.4 Add `POST /bug-reports` route (multipart: description + context fields + optional file), authenticated via the existing `get_validated_user` dependency; on success, uploads the screenshot (if present) using storage key convention `bug-reports/{bug_report_id}/{uuid4()}_{filename}`, persists the record, and enqueues the notification job.
- [x] 2.5 Add `enqueue_bug_report_notification(...)` to the existing `services/users/app/services/celery_client.py`, sending `tasks.feedback.post_notification` with the report id, description, context fields, and screenshot storage key (if any).
- [x] 2.6 Add Pydantic request/response schemas for the endpoint.
- [x] 2.7 Wire the new route in `nginx/nginx-dev.conf`, `nginx/nginx.conf`, and `Caddyfile`.
- [x] 2.8 Tests: successful submission with and without a screenshot, oversized file rejected, spoofed/disallowed content type rejected, unauthenticated request rejected, notification enqueue failure does not fail the submission response.
- [x] 2.9 Run `services/users` tests and lint clean; PR merged (`Closes #258`).

## 3. Worker notification task (services/worker) — depends on 1, pairs with 2

- [x] 3.1 Add `services/worker/tasks/feedback/post_notification.py`: task `tasks.feedback.post_notification` (`bind=True`, retry with backoff on `NotificationError`, following `send_password_reset_email`'s pattern) that builds a `NotificationMessage` from the task payload and sends it via the configured `NotificationProvider`.
- [x] 3.2 If the payload includes a screenshot storage key, generate a presigned download URL with a 24-hour expiry (explicit `expires_in`, not the 5-minute default) and set it as the message's `link`.
- [x] 3.3 Register the new task module in `celery_app.py`'s `include=[]` list and add a `task_routes` entry (new `feedback` queue or reuse an existing one).
- [x] 3.4 Add `SLACK_WEBHOOK_URL` (default `""`) to `services/worker/config.py` with a comment following the file's existing documentation convention, and add the key (left blank, or filled in only in the non-committed local env) to `.env.worker.dev` / `.env.worker.local` / `.env.worker.prod`. Flag to the user before committing any of these files if a real webhook value has been filled in.
- [x] 3.5 Tests: task constructs the expected message and presigned link, retry behavior on a simulated retryable failure, and `test_celery_task_registration.py` passes with the new module registered.
- [x] 3.6 Run `services/worker` tests and lint clean; PR merged (`Closes #259`).

## 4. Frontend widget wiring — depends on 2

- [x] 4.1 Build the "Report a problem" React component from the approved mockup (floating trigger, modal with free-text field, read-only context chips, optional screenshot attach, submit button, confirmation state).
- [x] 4.2 Capture context client-side (current page path, `navigator.userAgent`, client timestamp) and display it in the read-only chips before submission.
- [x] 4.3 Add the API call in `frontend-typescript/src/api/` to `POST /bug-reports` (multipart, including the optional screenshot file), and wire it to the modal's submit action and confirmation state.
- [x] 4.4 Mount the widget in the app shell so the trigger button is available on every authenticated page.
- [x] 4.5 Manually verify end-to-end in a running dev environment: submit with and without a screenshot, confirm the `bug_reports` record and the console/Slack notification both appear.
- [x] 4.6 Run frontend tests and lint clean; PR merged (`Closes #256, Closes #258, Closes #259`).
