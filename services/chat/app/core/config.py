import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # services/chat/app/core
env_mode = os.getenv("ENV", "development")
if env_mode == "local":
    ENV_FILE = BASE_DIR.parent / ".env.chat.private.local"
elif env_mode == "production":
    ENV_FILE = BASE_DIR.parent / ".env.chat.prod"
else:
    ENV_FILE = BASE_DIR.parent / ".env.chat.private.dev"


class Settings(BaseSettings):
    env: str = "development"
    debug: bool = True
    LOG_LEVEL: str = "INFO"

    chat_database_url: str
    BUDGET_SERVICE_URL: str = "http://localhost:8001/api/v1"
    AI_SERVICE_URL: str = "http://localhost:8002/api/v1"

    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=False, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
