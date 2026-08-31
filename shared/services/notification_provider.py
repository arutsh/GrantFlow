# /shared/services/notification_provider.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class NotificationError(Exception):
    """Raised when an outbound-notification provider can't be reached or rejects a send."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retryable: bool | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


@dataclass
class NotificationMessage:
    """Channel-neutral notification payload — no vendor-specific shape."""

    title: str
    body: str
    fields: list[tuple[str, str]] = field(default_factory=list)
    link: str | None = None


class NotificationProvider(ABC):
    """Base class every outbound-notification provider extends, so call sites
    depend on this shape instead of any vendor-specific channel API."""

    @abstractmethod
    def send(self, message: NotificationMessage) -> None: ...
