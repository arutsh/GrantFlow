import pytest

import tasks.email_client as svc
from config import settings
from shared.services.brevo_client import BrevoClient
from shared.services.console_email_client import ConsoleEmailClient
from shared.services.mailersend_client import MailerSendClient
from shared.services.mailjet_client import MailjetClient


@pytest.fixture(autouse=True)
def _reset_client_cache():
    svc._client = None
    yield
    svc._client = None


def test_mailersend_selected_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailersend")
    monkeypatch.setattr(settings, "MAILERSEND_API_TOKEN", "tok")
    monkeypatch.setattr(settings, "MAILERSEND_SENDER_EMAIL", "from@example.com")

    client = svc.get_email_client()

    assert isinstance(client, MailerSendClient)


def test_mailjet_selected_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailjet")
    monkeypatch.setattr(settings, "MAILJET_API_KEY", "key")
    monkeypatch.setattr(settings, "MAILJET_SECRET_KEY", "secret")
    monkeypatch.setattr(settings, "MAILJET_SENDER_EMAIL", "from@example.com")

    client = svc.get_email_client()

    assert isinstance(client, MailjetClient)


def test_brevo_selected_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "brevo")
    monkeypatch.setattr(settings, "BREVO_API_KEY", "key")
    monkeypatch.setattr(settings, "BREVO_SENDER_EMAIL", "from@example.com")

    client = svc.get_email_client()

    assert isinstance(client, BrevoClient)


def test_console_selected_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "console")

    client = svc.get_email_client()

    assert isinstance(client, ConsoleEmailClient)


def test_console_is_the_fallback_when_provider_is_blank(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "")

    client = svc.get_email_client()

    assert isinstance(client, ConsoleEmailClient)


def test_unsupported_provider_raises():
    settings.EMAIL_PROVIDER = "sendgrid"
    try:
        with pytest.raises(ValueError, match="Unsupported EMAIL_PROVIDER"):
            svc.get_email_client()
    finally:
        settings.EMAIL_PROVIDER = "console"


def test_client_is_cached_across_calls(monkeypatch):
    monkeypatch.setattr(settings, "EMAIL_PROVIDER", "mailersend")

    first = svc.get_email_client()
    second = svc.get_email_client()

    assert first is second
