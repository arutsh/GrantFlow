import os

# Must be set before any app modules are imported so pydantic-settings resolves them
os.environ.setdefault("AI_DATABASE_URL", "postgresql://test:test@localhost/test")
os.environ.setdefault("RABBITMQ_URL", "amqp://guest:guest@localhost:5672//")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ENV", "test")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
