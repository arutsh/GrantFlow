from urllib.parse import urlencode

from celery_app import app
from shared.services.email_provider import EmailProviderError
from tasks.email_client import get_email_client


@app.task(
    name="tasks.users.send_invite_email",
    bind=True,
    max_retries=5,
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def send_invite_email(
    self,
    email: str,
    token: str,
    first_name: str = "",
    inviter_name: str = "",
    company_name: str = "",
):
    from config import settings

    query = urlencode({"token": token, "email": email})
    invite_url = f"{settings.FRONTEND_BASE_URL}/accept-invite?{query}"
    client = get_email_client()
    # Var names below must match the dashboard template's placeholders.
    template_id = getattr(settings, f"{settings.EMAIL_PROVIDER.upper()}_INVITE_TEMPLATE_ID")
    try:
        client.send_template_email(
            to_email=email,
            to_name=first_name,
            subject=f"You've been invited to join {company_name or client.sender_name}",
            template_id=template_id,
            personalization={
                "name": first_name or "there",
                "inviter_name": inviter_name or "A teammate",
                "org_name": company_name or client.sender_name,
                "invite_url": invite_url,
                # Must track EMAIL_VERIFICATION_TOKEN_TTL_HOURS in user_crud.py.
                "expiry_hours": "24 hours",
                "support_email": client.sender_email,
            },
        )
    except EmailProviderError as exc:
        raise self.retry(exc=exc)
    return {"sent": True}
