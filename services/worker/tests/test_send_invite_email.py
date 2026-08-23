from unittest.mock import MagicMock

from config import settings
from tasks.users.send_invite_email import send_invite_email


def test_personalization_includes_privacy_url(monkeypatch):
    monkeypatch.setattr(settings, "FRONTEND_BASE_URL", "https://app.example.com")
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailersend")
    monkeypatch.setattr(settings, "MAILERSEND_INVITE_TEMPLATE_ID", "tmpl-2")

    mock_client = MagicMock()
    mock_client.sender_email = "support@example.com"
    mock_client.sender_name = "OpenGrantFlow"
    monkeypatch.setattr("tasks.users.send_invite_email.get_email_client", lambda: mock_client)

    send_invite_email(
        email="user@example.com",
        token="tok",
        first_name="Ana",
        inviter_name="Boss",
        company_name="Acme",
    )

    personalization = mock_client.send_template_email.call_args.kwargs["personalization"]
    assert personalization["privacy_url"] == "https://app.example.com/legal#privacy"
