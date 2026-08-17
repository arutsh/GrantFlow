from urllib.parse import urlencode

from celery_app import app
from shared.services.email_provider import EmailProviderError
from tasks.email_client import get_email_client


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
    client = get_email_client()
    # Template lives on the active provider's own dashboard, so the setting name
    # tracks EMAIL_PROVIDER (MAILERSEND_/MAILJET_)_VERIFICATION_TEMPLATE_ID.
    template_id = getattr(settings, f"{settings.EMAIL_PROVIDER.upper()}_VERIFICATION_TEMPLATE_ID")
    try:
        client.send_template_email(
            to_email=email,
            to_name=first_name,
            subject=f"Confirm your email for {client.sender_name}",
            template_id=template_id,
            personalization={
                "name": first_name or "there",
                "verify_url": verify_url,
                # Must track EMAIL_VERIFICATION_TOKEN_TTL_HOURS in
                # services/users/app/crud/user_crud.py — no shared constant
                # between the two services.
                "expiry_hours": 24,
                "support_email": client.sender_email,
                "account_name": client.sender_name,
            },
        )
    except EmailProviderError as exc:
        raise self.retry(exc=exc)
    return {"sent": True}
