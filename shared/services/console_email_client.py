# /shared/services/console_email_client.py
from shared.services.email_provider import EmailClient


class ConsoleEmailClient(EmailClient):
    """Local-dev-only provider: prints the send instead of calling a real vendor API."""

    def __init__(self, sender_email: str = "dev@localhost", sender_name: str = "GrandFlow"):
        super().__init__(sender_email, sender_name)

    def send_template_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        template_id: str,
        personalization: dict,
    ) -> None:
        lines = [
            "",
            "=" * 70,
            "EMAIL (console provider — not actually sent)",
            f"To:      {to_name or to_email} <{to_email}>",
            f"Subject: {subject}",
            f"Template: {template_id or '(none)'}",
            "Personalization:",
        ]
        for key, value in personalization.items():
            lines.append(f"  {key}: {value}")
        lines.append("=" * 70)
        print("\n".join(lines))
