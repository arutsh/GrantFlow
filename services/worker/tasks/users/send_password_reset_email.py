from urllib.parse import urlencode

from celery_app import app
from shared.services.email_provider import EmailProviderError
from tasks.email_client import get_email_client


@app.task(
    name="tasks.users.send_password_reset_email",
    bind=True,
    max_retries=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_password_reset_email(self, email: str, token: str, first_name: str = ""):
    from config import settings

    query = urlencode({"token": token, "email": email})
    reset_url = f"{settings.FRONTEND_BASE_URL}/reset-password?{query}"
    client = get_email_client()
    template_id = getattr(settings, f"{settings.EMAIL_PROVIDER.upper()}_PASSWORD_RESET_TEMPLATE_ID")
    try:
        client.send_template_email(
            to_email=email,
            to_name=first_name,
            subject=f"Reset your password for {client.sender_name}",
            template_id=template_id,
            personalization={
                "name": first_name or "there",
                "reset_url": reset_url,
                # Must track PASSWORD_RESET_TOKEN_TTL_HOURS in services/users/app/crud/user_crud.py.
                "expiry_hours": 1,
                "support_email": client.sender_email,
                "account_name": client.sender_name,
                "privacy_url": f"{settings.FRONTEND_BASE_URL}/legal#privacy",
            },
        )
    except EmailProviderError as exc:
        raise self.retry(exc=exc)
    return {"sent": True}
