# /shared/services/email_provider.py
from typing import Protocol


class EmailProviderError(Exception):
    """Raised when a transactional-email provider can't be reached or rejects a send.

    `status_code`/`retryable` are populated by each provider's client so a future
    retry-classification fix can consume them without another refactor; nothing
    reads them yet.
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


class EmailProvider(Protocol):
    """Interface every transactional-email provider client implements, so call
    sites depend on this shape instead of any vendor-specific payload/response."""

    def send_template_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        template_id: str,
        personalization: dict,
    ) -> None: ...
