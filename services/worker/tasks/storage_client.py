_storage_client = None


def get_storage_client():
    global _storage_client
    if _storage_client is None:
        from config import settings
        from shared.storage.client_builder import build_storage_client

        _storage_client = build_storage_client(settings)
    return _storage_client
