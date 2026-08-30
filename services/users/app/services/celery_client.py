from uuid import UUID

from celery import Celery
from app.core.config import settings

# Producer-only client: the users service enqueues tasks onto the same
# RabbitMQ broker services/worker consumes from, but never imports or runs
# worker task code itself.
celery_client = Celery("users_producer", broker=settings.RABBITMQ_URL)
celery_client.conf.task_routes = {
    "tasks.users.*": {"queue": "users"},
    "tasks.feedback.*": {"queue": "feedback"},
}


def enqueue_verification_email(email: str, token: str, first_name: str = "") -> None:
    celery_client.send_task(
        "tasks.users.send_verification_email",
        kwargs={"email": email, "token": token, "first_name": first_name},
    )


def enqueue_password_reset_email(email: str, token: str, first_name: str = "") -> None:
    celery_client.send_task(
        "tasks.users.send_password_reset_email",
        kwargs={"email": email, "token": token, "first_name": first_name},
    )


def enqueue_bug_report_notification(
    bug_report_id: UUID,
    description: str,
    page_path: str,
    user_agent: str,
    client_timestamp: str,
    screenshot_storage_key: str | None = None,
) -> None:
    celery_client.send_task(
        "tasks.feedback.post_notification",
        kwargs={
            "bug_report_id": str(bug_report_id),
            "description": description,
            "page_path": page_path,
            "user_agent": user_agent,
            "client_timestamp": client_timestamp,
            "screenshot_storage_key": screenshot_storage_key,
        },
    )


def enqueue_invite_email(
    email: str,
    token: str,
    first_name: str = "",
    inviter_name: str = "",
    company_name: str = "",
) -> None:
    celery_client.send_task(
        "tasks.users.send_invite_email",
        kwargs={
            "email": email,
            "token": token,
            "first_name": first_name,
            "inviter_name": inviter_name,
            "company_name": company_name,
        },
    )
