# /shared/services/console_notification_client.py
from shared.services.notification_provider import NotificationMessage, NotificationProvider


class ConsoleNotificationProvider(NotificationProvider):
    """No-destination-configured fallback: logs instead of calling out."""

    def send(self, message: NotificationMessage) -> None:
        lines = [
            "",
            "=" * 70,
            "NOTIFICATION (console provider — no destination configured)",
            f"Title: {message.title}",
            f"Body:  {message.body}",
        ]
        for name, value in message.fields:
            lines.append(f"  {name}: {value}")
        if message.link:
            lines.append(f"Link:  {message.link}")
        lines.append("=" * 70)
        print("\n".join(lines))
