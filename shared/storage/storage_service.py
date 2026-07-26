from abc import ABC, abstractmethod
from typing import BinaryIO


def safe_content_disposition(filename: str) -> str:
    """Build an 'attachment' Content-Disposition value safe to place in an
    HTTP header. Strips CR/LF/NUL (header/response-splitting) and escapes
    backslash/quote (so a filename can't break out of the quoted token) —
    filenames are user-supplied and must never be interpolated raw."""
    sanitized = filename.replace("\\", "\\\\").replace('"', '\\"')
    sanitized = "".join(ch for ch in sanitized if ch not in ("\r", "\n", "\x00"))
    return f'attachment; filename="{sanitized}"'


class StorageService(ABC):
    """File storage interface.

    Concrete backends (S3StorageService today; others later) implement
    save/open_stream/delete/exists so callers never depend on a specific
    provider — swapping backends means picking a different subclass, not
    touching calling code.
    """

    @abstractmethod
    def save(self, key: str, data: bytes | BinaryIO, content_type: str | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    def open_stream(self, key: str) -> BinaryIO:
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def presigned_download_url(
        self,
        key: str,
        *,
        content_type: str | None = None,
        filename: str | None = None,
        expires_in: int = 300,
    ) -> str:
        raise NotImplementedError
