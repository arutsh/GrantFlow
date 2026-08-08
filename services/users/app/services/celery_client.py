from celery import Celery
from app.core.config import settings

# Producer-only client: the users service enqueues tasks onto the same
# RabbitMQ broker services/worker consumes from, but never imports or runs
# worker task code itself.
celery_client = Celery("users_producer", broker=settings.RABBITMQ_URL)
celery_client.conf.task_routes = {"tasks.users.*": {"queue": "users"}}


def enqueue_verification_email(email: str, token: str, first_name: str = "") -> None:
    celery_client.send_task(
        "tasks.users.send_verification_email",
        kwargs={"email": email, "token": token, "first_name": first_name},
    )
