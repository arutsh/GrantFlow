from celery import Celery
from celery.schedules import crontab
from config import settings

app = Celery(
    "grandflow_worker",
    broker=settings.RABBITMQ_URL,
    backend=settings.REDIS_URL,
    include=[
        "tasks.ai.cleanup_sessions",
        "tasks.debug.ping",
        "tasks.users.send_verification_email",
    ],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "tasks.ai.*": {"queue": "ai"},
        "tasks.budget.*": {"queue": "budget"},
        "tasks.users.*": {"queue": "users"},
        "tasks.debug.*": {"queue": "ai"},
    },
    beat_schedule={
        "cleanup-ai-sessions-daily": {
            "task": "tasks.ai.cleanup_sessions",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)
