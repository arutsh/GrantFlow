from urllib.parse import urlencode

from celery_app import app
from shared.services.mailersend_client import MailerSendClient, MailerSendError

_client = None


def _get_client():
    global _client
    if _client is None:
        from config import settings

        _client = MailerSendClient(
            api_token=settings.MAILERSEND_API_TOKEN,
            sender_email=settings.MAILERSEND_SENDER_EMAIL,
            sender_name=settings.MAILERSEND_SENDER_NAME,
            api_url=settings.MAILERSEND_API_URL or None,
        )
    return _client


@app.task(
    name="tasks.users.send_verification_email",
    bind=True,
    max_retries=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_verification_email(self, email: str, token: str, first_name: str = ""):
    from config import settings

    query = urlencode({"token": token, "email": email})
    verify_url = f"{settings.FRONTEND_BASE_URL}/verify-email?{query}"
    try:
        _get_client().send_template_email(
            to_email=email,
            to_name=first_name,
            subject=f"Confirm your email for {settings.MAILERSEND_SENDER_NAME}",
            template_id=settings.MAILERSEND_VERIFICATION_TEMPLATE_ID,
            personalization={
                "name": first_name or "there",
                "verify_url": verify_url,
                # Must track EMAIL_VERIFICATION_TOKEN_TTL_HOURS in
                # services/users/app/crud/user_crud.py — no shared constant
                # between the two services.
                "expiry_hours": 24,
                "support_email": settings.MAILERSEND_SENDER_EMAIL,
                "account": {"name": settings.MAILERSEND_SENDER_NAME},
            },
        )
    except MailerSendError as exc:
        raise self.retry(exc=exc)
    return {"sent": True}
