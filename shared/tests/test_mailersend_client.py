"""Tests for shared/services/mailersend_client per the transactional-email spec."""

import json

import httpx
import pytest

from shared.services.mailersend_client import MailerSendClient, MailerSendError


def _client(handler, **kwargs) -> MailerSendClient:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(
        transport=transport,
        headers={"Authorization": "Bearer tok", "Content-Type": "application/json"},
    )
    return MailerSendClient(
        api_token="tok",
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
            captured["headers"] = request.headers
            captured["body"] = json.loads(request.content)
            return httpx.Response(202, json={})

        client = _client(handler)
        client.send_template_email(
            to_email="ada@example.com",
            to_name="Ada",
            subject="Confirm your email",
            template_id="tmpl-1",
            personalization=_personalization(),
        )

        assert captured["headers"]["authorization"] == "Bearer tok"
        body = captured["body"]
        assert body["from"] == {"email": "from@example.com", "name": "GrandFlow"}
        assert body["to"] == [{"email": "ada@example.com", "name": "Ada"}]
        assert body["subject"] == "Confirm your email"
        assert body["template_id"] == "tmpl-1"
        assert body["personalization"] == [{"email": "ada@example.com", "data": _personalization()}]

    def test_http_error_raises_mailersend_error_with_status_and_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(422, text="invalid recipient")

        client = _client(handler)
        with pytest.raises(MailerSendError) as exc_info:
            client.send_template_email(
                to_email="ada@example.com",
                to_name="Ada",
                subject="Confirm your email",
                template_id="tmpl-1",
                personalization=_personalization(),
            )

        assert exc_info.value.status_code == 422
        assert exc_info.value.retryable is False

    def test_server_error_is_marked_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        client = _client(handler)
        with pytest.raises(MailerSendError) as exc_info:
            client.send_template_email(
                to_email="ada@example.com",
                to_name="Ada",
                subject="Confirm your email",
                template_id="tmpl-1",
                personalization=_personalization(),
            )

        assert exc_info.value.status_code == 500
        assert exc_info.value.retryable is True

    def test_network_error_raises_mailersend_error(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        client = _client(handler)
        with pytest.raises(MailerSendError) as exc_info:
            client.send_template_email(
                to_email="ada@example.com",
                to_name="Ada",
                subject="Confirm your email",
                template_id="tmpl-1",
                personalization=_personalization(),
            )

        assert exc_info.value.status_code is None
        assert exc_info.value.retryable is True
