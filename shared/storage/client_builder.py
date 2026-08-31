from shared.storage.s3_storage_service import S3StorageService
from shared.storage.storage_service import StorageService


def build_storage_client(settings) -> StorageService:
    """Build the S3-compatible storage client from a service's own Settings object."""
    return S3StorageService(
        endpoint_url=settings.STORAGE_ENDPOINT_URL,
        access_key=settings.STORAGE_ACCESS_KEY,
        secret_key=settings.STORAGE_SECRET_KEY,
        bucket_name=settings.STORAGE_BUCKET_NAME,
    )
