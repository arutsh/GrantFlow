# /shared/services/email_provider.py
from abc import ABC, abstractmethod


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


class EmailClient(ABC):
    """Base class every transactional-email provider client extends, so call
    sites depend on this shape instead of any vendor-specific payload/response."""

    def __init__(self, sender_email: str, sender_name: str = "GrandFlow"):
        self.sender_email = sender_email
        self.sender_name = sender_name

    @abstractmethod
    def send_template_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        template_id: str,
        personalization: dict,
    ) -> None: ...
