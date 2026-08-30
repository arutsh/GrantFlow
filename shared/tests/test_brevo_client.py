"""Tests for shared/services/brevo_client per the transactional-email spec."""

import json

import httpx
import pytest

from shared.services.brevo_client import BrevoClient, BrevoError


def _client(handler, **kwargs) -> BrevoClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport, headers={"api-key": "key"})
    return BrevoClient(
        api_key="key",
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
            captured["api_key"] = request.headers["api-key"]
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

        assert captured["api_key"] == "key"
        body = captured["body"]
        assert body["sender"] == {"email": "from@example.com", "name": "GrandFlow"}
        assert body["to"] == [{"email": "ada@example.com", "name": "Ada"}]
        assert body["subject"] == "Confirm your email"
        assert body["templateId"] == 12345
        assert body["params"] == _personalization()

    def test_http_error_raises_brevo_error_with_status_and_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, text="invalid template")

        client = _client(handler)
        with pytest.raises(BrevoError) as exc_info:
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
        with pytest.raises(BrevoError) as exc_info:
            client.send_template_email(
                to_email="ada@example.com",
                to_name="Ada",
                subject="Confirm your email",
                template_id="12345",
                personalization=_personalization(),
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.retryable is True

    def test_network_error_raises_brevo_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        client = _client(handler)
        with pytest.raises(BrevoError) as exc_info:
            client.send_template_email(
                to_email="ada@example.com",
                to_name="Ada",
                subject="Confirm your email",
                template_id="12345",
                personalization=_personalization(),
            )

        assert exc_info.value.status_code is None
        assert exc_info.value.retryable is True
