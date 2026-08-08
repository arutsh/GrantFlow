import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Required env vars:
#   RABBITMQ_URL  — amqp://user:pass@host:5672//
#   REDIS_URL     — redis://host:6379/0
#   AI_DATABASE_URL — postgresql://user:pass@host:5432/grandflow_ai
#   MAILERSEND_API_TOKEN    — MailerSend Email API token
#   MAILERSEND_SENDER_DOMAIN — trial domain in dev/staging, verified domain in prod
#   MAILERSEND_SENDER_EMAIL — from-address sent with each email (must belong to the sender domain)
#   MAILERSEND_VERIFICATION_TEMPLATE_ID — MailerSend dashboard template ID for the
#                                          verification email
#   MAILERSEND_API_URL — override for the MailerSend Email API endpoint; blank uses the real
#                         MailerSend API (only set this to point at a local mock in dev)
#   FRONTEND_BASE_URL — origin used to build the verification link, e.g. https://app.example.com

BASE_DIR = Path(__file__).resolve().parent
env_mode = os.getenv("ENV", "development")
if env_mode == "local":
    ENV_FILE = BASE_DIR / ".env.worker.local"
elif env_mode == "production":
    ENV_FILE = BASE_DIR / ".env.worker.prod"
elif env_mode == "test":
    ENV_FILE = BASE_DIR / ".env.worker.test"
else:
    ENV_FILE = BASE_DIR / ".env.worker.dev"


class Settings(BaseSettings):
    env: str = "development"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"
    REDIS_URL: str = "redis://localhost:6379/0"
    AI_DATABASE_URL: str
    MAILERSEND_API_TOKEN: str = ""
    MAILERSEND_SENDER_DOMAIN: str = ""
    MAILERSEND_SENDER_EMAIL: str = ""
    MAILERSEND_SENDER_NAME: str = "OpenGrandFlow"
    MAILERSEND_VERIFICATION_TEMPLATE_ID: str = ""
    MAILERSEND_API_URL: str = ""
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=False, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
