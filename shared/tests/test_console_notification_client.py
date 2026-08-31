"""Tests for shared/services/console_notification_client per the outbound-notifications spec."""

from shared.services.console_notification_client import ConsoleNotificationProvider
from shared.services.notification_provider import NotificationMessage


def test_send_prints_title_body_fields_and_link(capsys):
    provider = ConsoleNotificationProvider()

    provider.send(
        NotificationMessage(
            title="New bug report",
            body="Something broke",
            fields=[("Page", "/budgets/123")],
            link="https://s3.example.com/screenshot.png",
        )
    )

    out = capsys.readouterr().out
    assert "New bug report" in out
    assert "Something broke" in out
    assert "/budgets/123" in out
    assert "https://s3.example.com/screenshot.png" in out


def test_send_never_raises_with_no_fields_or_link():
    provider = ConsoleNotificationProvider()
    provider.send(NotificationMessage(title="t", body="b", fields=[], link=None))
