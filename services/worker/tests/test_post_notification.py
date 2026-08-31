from unittest.mock import MagicMock, patch

from config import settings
from shared.services.notification_provider import NotificationError
from tasks.feedback.post_notification import post_notification


def _payload(**overrides):
    defaults = dict(
        bug_report_id="report-1",
        description="Something broke",
        page_path="/budgets/123",
        user_agent="Mozilla/5.0",
        client_timestamp="2026-08-30T12:00:00+00:00",
        screenshot_storage_key=None,
    )
    defaults.update(overrides)
    return defaults


def _fake_provider():
    provider = MagicMock()
    return provider


class TestBuildsMessage:
    def test_message_without_screenshot(self, monkeypatch):
        provider = _fake_provider()
        monkeypatch.setattr(
            "tasks.feedback.post_notification.get_notification_provider", lambda url: provider
        )

        post_notification(**_payload())

        message = provider.send.call_args.args[0]
        assert message.title == "New bug report"
        assert message.body == "Something broke"
        assert ("Report ID", "report-1") in message.fields
        assert ("Page", "/budgets/123") in message.fields
        assert ("Browser", "Mozilla/5.0") in message.fields
        # A direct call (as opposed to .apply_async()) has no real task id.
        assert ("Delivery ID", "unknown") in message.fields
        assert message.link is None

    def test_message_with_screenshot_includes_presigned_link(self, monkeypatch):
        provider = _fake_provider()
        storage = MagicMock()
        storage.presigned_download_url.return_value = "https://minio.local/signed-url"
        monkeypatch.setattr(
            "tasks.feedback.post_notification.get_notification_provider", lambda url: provider
        )
        monkeypatch.setattr(
            "tasks.feedback.post_notification.get_storage_client", lambda: storage
        )

        post_notification(**_payload(screenshot_storage_key="bug-reports/1/x.png"))

        storage.presigned_download_url.assert_called_once_with(
            "bug-reports/1/x.png", expires_in=60 * 60 * 24
        )
        message = provider.send.call_args.args[0]
        assert message.link == "https://minio.local/signed-url"

    def test_delivery_id_is_the_real_task_id_when_dispatched(self, monkeypatch):
        provider = _fake_provider()
        monkeypatch.setattr(
            "tasks.feedback.post_notification.get_notification_provider", lambda url: provider
        )

        result = post_notification.apply(kwargs=_payload())

        message = provider.send.call_args.args[0]
        delivery_id = dict(message.fields)["Delivery ID"]
        assert delivery_id == result.id
        assert delivery_id != "unknown"


class TestRetryBehavior:
    def test_retryable_failure_calls_self_retry(self, monkeypatch):
        provider = _fake_provider()
        exc = NotificationError("timeout", retryable=True)
        provider.send.side_effect = exc
        monkeypatch.setattr(
            "tasks.feedback.post_notification.get_notification_provider", lambda url: provider
        )
        monkeypatch.setattr(settings, "SLACK_WEBHOOK_URL", "https://hooks.slack.com/x")

        with patch.object(post_notification, "retry", side_effect=exc) as mock_retry:
            try:
                post_notification(**_payload())
            except NotificationError:
                pass
        mock_retry.assert_called_once()
        assert mock_retry.call_args.kwargs["exc"] is exc

    def test_non_retryable_failure_does_not_retry(self, monkeypatch):
        provider = _fake_provider()
        exc = NotificationError("invalid_payload", retryable=False)
        provider.send.side_effect = exc
        monkeypatch.setattr(
            "tasks.feedback.post_notification.get_notification_provider", lambda url: provider
        )

        with patch.object(post_notification, "retry") as mock_retry:
            try:
                post_notification(**_payload())
            except NotificationError:
                pass
        mock_retry.assert_not_called()
