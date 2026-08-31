# /shared/services/slack_webhook_client.py
from typing import Any

import httpx

from shared.services.notification_provider import (
    NotificationError,
    NotificationMessage,
    NotificationProvider,
)


class SlackWebhookError(NotificationError):
    """Raised when a Slack Incoming Webhook call can't be reached or is rejected."""


class SlackWebhookProvider(NotificationProvider):
    """Posts a Block-Kit message to a Slack Incoming Webhook (free-plan compatible)."""

    def __init__(self, webhook_url: str, timeout: float = 15.0, http: httpx.Client | None = None):
        self.webhook_url = webhook_url
        self.http = http if http is not None else httpx.Client(timeout=timeout)

    def send(self, message: NotificationMessage) -> None:
        payload = {"blocks": self._build_blocks(message)}
        try:
            resp = self.http.post(self.webhook_url, json=payload)
        except httpx.RequestError as exc:
            raise SlackWebhookError(f"Could not reach Slack: {exc}", retryable=True) from exc

        if resp.status_code >= 400:
            raise SlackWebhookError(
                f"Slack webhook returned {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code,
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )

    @staticmethod
    def _build_blocks(message: NotificationMessage) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = [
            {"type": "header", "text": {"type": "plain_text", "text": message.title}},
            {"type": "section", "text": {"type": "mrkdwn", "text": message.body}},
        ]
        if message.fields:
            blocks.append(
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*{name}*\n{value}"}
                        for name, value in message.fields
                    ],
                }
            )
        if message.link:
            blocks.append(
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"<{message.link}|View attachment>"},
                }
            )
        return blocks
