"""Tests for shared/services/console_email_client per the transactional-email spec."""

from shared.services.console_email_client import ConsoleEmailClient


def test_send_template_email_prints_recipient_subject_and_personalization(capsys):
    client = ConsoleEmailClient(sender_email="dev@localhost", sender_name="GrandFlow")

    client.send_template_email(
        to_email="ada@example.com",
        to_name="Ada",
        subject="Reset your password",
        template_id="reset-template",
        personalization={"name": "Ada", "reset_url": "http://x/reset?token=abc"},
    )

    out = capsys.readouterr().out
    assert "ada@example.com" in out
    assert "Reset your password" in out
    assert "reset-template" in out
    assert "http://x/reset?token=abc" in out


def test_send_template_email_never_raises():
    client = ConsoleEmailClient()
    client.send_template_email(
        to_email="ada@example.com",
        to_name="",
        subject="Confirm your email",
        template_id="",
        personalization={},
    )
