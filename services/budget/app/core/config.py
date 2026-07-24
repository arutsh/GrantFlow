import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # services/budget/app/core
# ENV_FILE = BASE_DIR.parent / ".env.budget.dev"
# Determine which env file to load based on environment
env_mode = os.getenv("ENV", "development")
if env_mode == "local":
    ENV_FILE = BASE_DIR.parent / ".env.budget.private.local"
elif env_mode == "production":
    ENV_FILE = BASE_DIR.parent / ".env.budget.prod"
else:
    ENV_FILE = BASE_DIR.parent / ".env.budget.private.dev"
print(f"Base dir-envfile: {BASE_DIR}, {ENV_FILE}")


class Settings(BaseSettings):
    env: str = "development"
    debug: bool = True

    # Service URLs
    customer_service_url: str
    user_service_url: str
    user_all_services_url: str
    REDIS_URL: str
    RULE_BASED_MAPPING_ENABLED: bool = False
    USE_SEMANTIC_EMBEDDINGS: bool = True  # Use Sentence Transformers for embeddings
    # Databases
    budget_database_url: str
    # Object storage (S3-compatible: MinIO locally, Cloudflare R2 in production)
    STORAGE_ENDPOINT_URL: str
    STORAGE_ACCESS_KEY: str
    STORAGE_SECRET_KEY: str
    STORAGE_BUCKET_NAME: str
    # RabbitMQ
    RABBITMQ_URL: str
    RABBITMQ_EXCHANGE: str
    RABBITMQ_QUEUE: str
    LOG_LEVEL: str

    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=False, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
print(f"Base dir: {BASE_DIR}")
print(f"settings.debug: {settings.debug}")
print(f"settings.budget_database_url: {settings.budget_database_url}")
print(f"settings.customer_service_url: {settings.customer_service_url}")
print(f"settings.REDIS_URL: {settings.REDIS_URL}")
print(f"settings.RULE_BASED_MAPPING_ENABLED: {settings.RULE_BASED_MAPPING_ENABLED}")
print(f"settings.USE_SEMANTIC_EMBEDDINGS: {settings.USE_SEMANTIC_EMBEDDINGS}")
# print(f"Allowed origins: {settings.ALLOWED_ORIGINS}")
