import io
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from shared.storage.storage_service import StorageService


class S3StorageService(StorageService):
    """S3-compatible object storage backend (MinIO, Cloudflare R2, AWS S3, ...).

    The only module in the repo permitted to import boto3 — callers only
    ever see the save/open_stream/delete/exists interface, so swapping the
    backing provider via config never touches calling code.
    """

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket_name: str,
    ):
        self.bucket_name = bucket_name
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )

    def _ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self.bucket_name)
        except ClientError:
            self._client.create_bucket(Bucket=self.bucket_name)

    def save(self, key: str, data: bytes | BinaryIO, content_type: str | None = None) -> None:
        self._ensure_bucket()
        fileobj = io.BytesIO(data) if isinstance(data, bytes) else data
        extra_args = {"ContentType": content_type} if content_type else {}
        self._client.upload_fileobj(fileobj, self.bucket_name, key, ExtraArgs=extra_args)

    def open_stream(self, key: str) -> BinaryIO:
        response = self._client.get_object(Bucket=self.bucket_name, Key=key)
        return response["Body"]

    def delete(self, key: str) -> None:
        self._client.delete_object(Bucket=self.bucket_name, Key=key)

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except ClientError:
            return False
