"""
Tests for ticket #145: StorageService round-trip against local MinIO.

Requires the local MinIO container (docker-compose's `minio` service) to be
running — skipped automatically otherwise, since CI doesn't provision one.
Exercising a real S3-compatible backend (rather than a filesystem
stand-in) is the whole point of this design — see design.md.
"""

import uuid
import os

import pytest
from botocore.exceptions import ClientError, EndpointConnectionError

from shared.storage.s3_storage_service import S3StorageService

ENDPOINT_URL = os.environ.get("STORAGE_ENDPOINT_URL", "http://localhost:9000")
ACCESS_KEY = os.environ.get("STORAGE_ACCESS_KEY", "minioadmin")
SECRET_KEY = os.environ.get("STORAGE_SECRET_KEY", "minioadmin")
BUCKET_NAME = os.environ.get("STORAGE_BUCKET_NAME", "grantflow-reports-dev")


@pytest.fixture
def storage():
    service = S3StorageService(
        endpoint_url=ENDPOINT_URL,
        access_key=ACCESS_KEY,
        secret_key=SECRET_KEY,
        bucket_name=BUCKET_NAME,
    )
    try:
        service.exists("healthcheck-probe")
    except EndpointConnectionError:
        pytest.skip(f"MinIO not reachable at {ENDPOINT_URL} — start it via docker-compose")
    return service


def test_save_and_open_stream_round_trip(storage):
    key = f"test/{uuid.uuid4()}.txt"
    storage.save(key, b"hello storage", content_type="text/plain")

    body = storage.open_stream(key).read()

    assert body == b"hello storage"
    storage.delete(key)


def test_exists_reflects_save_and_delete(storage):
    key = f"test/{uuid.uuid4()}.txt"
    assert storage.exists(key) is False

    storage.save(key, b"payload")
    assert storage.exists(key) is True

    storage.delete(key)
    assert storage.exists(key) is False


def test_delete_makes_key_unreadable(storage):
    key = f"test/{uuid.uuid4()}.txt"
    storage.save(key, b"payload")
    storage.delete(key)

    with pytest.raises(ClientError):
        storage.open_stream(key)
