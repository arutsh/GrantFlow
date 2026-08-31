"""Tests for shared/services/notification_client provider-selection helper."""

from shared.services.console_notification_client import ConsoleNotificationProvider
from shared.services.notification_client import get_notification_provider
from shared.services.slack_webhook_client import SlackWebhookProvider


def test_returns_slack_provider_when_webhook_url_configured():
    provider = get_notification_provider("https://hooks.slack.com/services/x")
    assert isinstance(provider, SlackWebhookProvider)


def test_returns_console_provider_when_webhook_url_blank():
    assert isinstance(get_notification_provider(""), ConsoleNotificationProvider)


def test_returns_console_provider_when_webhook_url_none():
    assert isinstance(get_notification_provider(None), ConsoleNotificationProvider)
