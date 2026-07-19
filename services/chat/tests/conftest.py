import os

os.environ.setdefault("CHAT_DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

from main import app  # noqa: E402,F401
