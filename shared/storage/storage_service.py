from abc import ABC, abstractmethod
from typing import BinaryIO


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
