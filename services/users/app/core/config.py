import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # services/users/app/core

# Environment-aware env file selection
ENV = os.getenv("ENV", "development")
if ENV == "local":
    ENV_FILE = BASE_DIR.parent / ".env.users.local"
elif ENV == "production":
    ENV_FILE = BASE_DIR.parent / ".env.users.prod"
else:
    ENV_FILE = BASE_DIR.parent / ".env.users.dev"

print(f"Base dir-envfile: {BASE_DIR}, {ENV_FILE}")


class Settings(BaseSettings):
    env: str = "development"
    debug: bool = True
    users_database_url: str
    REDIS_URL: str
    RABBITMQ_URL: str
    RABBITMQ_EXCHANGE: str
    LOG_LEVEL: str
    AI_SERVICE_URL: str = "http://localhost:8082/api/v1"
    BUDGET_SERVICE_URL: str = "http://localhost:8001/api/v1"
    LOGIN_MAX_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_SECONDS: int = 900
    # Only ever true in .env.users.local (local dev + e2e CI, both boot from
    # docker-compose.local.yml) — never set in .env.users.dev/.env.users.prod.
    # Lets e2e drive the real /auth/verify-email flow without a real inbox.
    EXPOSE_VERIFICATION_TOKEN_FOR_TESTS: bool = False
    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=False, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
print(f"Base dir: {BASE_DIR}")
print(f"settings.users_database_url: {settings.users_database_url}")
print(f"settings.debug: {settings.debug}")
# print(f"allowed origins: {settings.ALLOWED_ORIGINS}")
