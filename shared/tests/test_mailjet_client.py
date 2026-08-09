"""Tests for shared/services/mailjet_client per the transactional-email spec."""

import json

import httpx
import pytest

from shared.services.mailjet_client import MailjetClient, MailjetError


def _client(handler, **kwargs) -> MailjetClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, auth=("key", "secret"))
    return MailjetClient(
        api_key="key",
        secret_key="secret",
        sender_email="from@example.com",
        sender_name="GrandFlow",
        http=http,
        **kwargs,
    )


def _personalization() -> dict:
    return {"name": "Ada", "verify_url": "http://x/verify", "expiry_hours": 24}


class TestSendTemplateEmail:
    def test_success_posts_expected_payload(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers["authorization"]
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, json={})

        client = _client(handler)
        client.send_template_email(
            to_email="ada@example.com",
            to_name="Ada",
            subject="Confirm your email",
            template_id="12345",
            personalization=_personalization(),
        )

        assert captured["auth"].startswith("Basic ")
        message = captured["body"]["Messages"][0]
        assert message["From"] == {"Email": "from@example.com", "Name": "GrandFlow"}
        assert message["To"] == [{"Email": "ada@example.com", "Name": "Ada"}]
        assert message["Subject"] == "Confirm your email"
        assert message["TemplateID"] == 12345
        assert message["TemplateLanguage"] is True
        assert message["Variables"] == _personalization()

    def test_http_error_raises_mailjet_error_with_status_and_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, text="invalid template")

        client = _client(handler)
        with pytest.raises(MailjetError) as exc_info:
            client.send_template_email(
                to_email="ada@example.com",
                to_name="Ada",
                subject="Confirm your email",
                template_id="12345",
                personalization=_personalization(),
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.retryable is False

    def test_server_error_is_marked_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        client = _client(handler)
        with pytest.raises(MailjetError) as exc_info:
            client.send_template_email(
                to_email="ada@example.com",
                to_name="Ada",
                subject="Confirm your email",
                template_id="12345",
                personalization=_personalization(),
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.retryable is True

    def test_network_error_raises_mailjet_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        client = _client(handler)
        with pytest.raises(MailjetError) as exc_info:
            client.send_template_email(
                to_email="ada@example.com",
                to_name="Ada",
                subject="Confirm your email",
                template_id="12345",
                personalization=_personalization(),
            )

        assert exc_info.value.status_code is None
        assert exc_info.value.retryable is True
