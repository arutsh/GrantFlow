import os
from dataclasses import dataclass


@dataclass(frozen=True)
class StorageConfig:
    endpoint_url: str
    access_key: str
    secret_key: str
    bucket_name: str


def load_storage_config() -> StorageConfig:
    return StorageConfig(
        endpoint_url=os.environ["STORAGE_ENDPOINT_URL"],
        access_key=os.environ["STORAGE_ACCESS_KEY"],
        secret_key=os.environ["STORAGE_SECRET_KEY"],
        bucket_name=os.environ["STORAGE_BUCKET_NAME"],
    )
