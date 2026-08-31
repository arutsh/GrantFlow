"""Tests for shared/services/slack_webhook_client per the outbound-notifications spec."""

import json

import httpx
import pytest

from shared.services.notification_provider import NotificationMessage
from shared.services.slack_webhook_client import SlackWebhookError, SlackWebhookProvider


def _provider(handler) -> SlackWebhookProvider:
    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    return SlackWebhookProvider(webhook_url="https://hooks.slack.com/services/x", http=http)


def _message(
    title: str = "New bug report",
    body: str = "Something broke",
    fields: list[tuple[str, str]] | None = None,
    link: str | None = None,
) -> NotificationMessage:
    default_fields = [("Page", "/budgets/123"), ("Browser", "Chrome/120")]
    return NotificationMessage(
        title=title,
        body=body,
        fields=fields if fields is not None else default_fields,
        link=link,
    )


class TestSend:
    def test_success_posts_expected_blocks(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, text="ok")

        _provider(handler).send(_message())

        blocks = captured["body"]["blocks"]
        assert blocks[0]["text"]["text"] == "New bug report"
        assert blocks[1]["text"]["text"] == "Something broke"
        field_texts = [f["text"] for f in blocks[2]["fields"]]
        assert "*Page*\n/budgets/123" in field_texts
        assert "*Browser*\nChrome/120" in field_texts

    def test_link_included_as_clickable_text(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["body"] = json.loads(request.content)
            return httpx.Response(200, text="ok")

        _provider(handler).send(_message(link="https://s3.example.com/screenshot.png"))

        last_block = captured["body"]["blocks"][-1]
        link_text = last_block["text"]["text"]
        assert "<https://s3.example.com/screenshot.png|View attachment>" in link_text

    def test_network_error_is_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("boom", request=request)

        with pytest.raises(SlackWebhookError) as exc_info:
            _provider(handler).send(_message())

        assert exc_info.value.retryable is True
        assert exc_info.value.status_code is None

    def test_server_error_is_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        with pytest.raises(SlackWebhookError) as exc_info:
            _provider(handler).send(_message())

        assert exc_info.value.status_code == 500
        assert exc_info.value.retryable is True

    def test_rate_limited_is_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, text="rate limited")

        with pytest.raises(SlackWebhookError) as exc_info:
            _provider(handler).send(_message())

        assert exc_info.value.status_code == 429
        assert exc_info.value.retryable is True

    def test_bad_request_is_not_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(400, text="invalid_payload")

        with pytest.raises(SlackWebhookError) as exc_info:
            _provider(handler).send(_message())

        assert exc_info.value.status_code == 400
        assert exc_info.value.retryable is False

    def test_not_found_is_not_retryable(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(404, text="no_service")

        with pytest.raises(SlackWebhookError) as exc_info:
            _provider(handler).send(_message())

        assert exc_info.value.status_code == 404
        assert exc_info.value.retryable is False
