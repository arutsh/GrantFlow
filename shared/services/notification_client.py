# /shared/services/notification_client.py
from shared.services.console_notification_client import ConsoleNotificationProvider
from shared.services.notification_provider import NotificationProvider
from shared.services.slack_webhook_client import SlackWebhookProvider


def get_notification_provider(webhook_url: str | None) -> NotificationProvider:
    """Env-driven selection: a configured webhook URL gets Slack, otherwise console."""
    if webhook_url:
        return SlackWebhookProvider(webhook_url=webhook_url)
    return ConsoleNotificationProvider()
