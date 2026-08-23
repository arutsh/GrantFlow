from unittest.mock import MagicMock

from config import settings
from tasks.users.send_verification_email import send_verification_email


def test_personalization_includes_privacy_url(monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "https://app.example.com")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailersend")
    monkeypatch.setattr(settings, "MAILERSEND_VERIFICATION_TEMPLATE_ID", "tmpl-1")

    mock_client = MagicMock()
    mock_client.sender_email = "support@example.com"
    mock_client.sender_name = "OpenGrantFlow"
    monkeypatch.setattr(
        "tasks.users.send_verification_email.get_email_client", lambda: mock_client
    )

    send_verification_email(email="user@example.com", token="tok", first_name="Ana")

    personalization = mock_client.send_template_email.call_args.kwargs["personalization"]
    assert personalization["privacy_url"] == "https://app.example.com/legal#privacy"
