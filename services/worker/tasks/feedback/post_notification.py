from celery_app import app
from shared.services.notification_client import get_notification_provider
from shared.services.notification_provider import NotificationError, NotificationMessage
from tasks.storage_client import get_storage_client

SCREENSHOT_LINK_EXPIRY_SECONDS = 60 * 60 * 24


@app.task(
    name="tasks.feedback.post_notification",
    bind=True,
    max_retries=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def post_notification(
    self,
    bug_report_id: str,
    description: str,
    page_path: str,
    user_agent: str,
    client_timestamp: str,
    screenshot_storage_key: str | None = None,
):
    from config import settings

    link = None
    if screenshot_storage_key:
        # Longer than S3StorageService's 5-minute default: a Slack message
        # may be opened hours after the report was filed.
        link = get_storage_client().presigned_download_url(
            screenshot_storage_key, expires_in=SCREENSHOT_LINK_EXPIRY_SECONDS
        )

    message = NotificationMessage(
        title="New bug report",
        body=description,
        fields=[
            ("Report ID", bug_report_id),
            ("Page", page_path),
            ("Browser", user_agent),
            ("Reported at", client_timestamp),
            # Stable across Celery retries of this same dispatch (self.retry()
            # keeps the task id) — lets a human spot a retry-caused duplicate.
            ("Delivery ID", self.request.id or "unknown"),
        ],
        link=link,
    )

    provider = get_notification_provider(settings.SLACK_WEBHOOK_URL)
    try:
        provider.send(message)
    except NotificationError as exc:
        if exc.retryable:
            raise self.retry(exc=exc)
        raise
    return {"sent": True}
