from app.core.config import settings
from shared.storage.client_builder import build_storage_client
from shared.storage.storage_service import StorageService

storage_client: StorageService = build_storage_client(settings)
