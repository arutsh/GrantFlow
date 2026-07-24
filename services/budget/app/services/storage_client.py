from app.core.config import settings
from shared.storage.storage_service import StorageService
from shared.storage.s3_storage_service import S3StorageService

storage_client: StorageService = S3StorageService(
    endpoint_url=settings.STORAGE_ENDPOINT_URL,
    access_key=settings.STORAGE_ACCESS_KEY,
    secret_key=settings.STORAGE_SECRET_KEY,
    bucket_name=settings.STORAGE_BUCKET_NAME,
)
