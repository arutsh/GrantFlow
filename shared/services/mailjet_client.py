# /shared/services/mailjet_client.py
import httpx

from shared.services.email_provider import EmailClient, EmailProviderError

DEFAULT_MAILJET_API_URL = "https://api.mailjet.com/v3.1/send"


class MailjetError(EmailProviderError):
    """Raised when the Mailjet Send API can't be reached or rejects a send."""


class MailjetClient(EmailClient):
    """Thin wrapper around Mailjet's Send API v3.1.

    One client (and its underlying httpx client) is meant to be built once
    per process and reused across sends, not constructed per-call.
    """

    def __init__(
        self,
        api_key: str,
        secret_key: str,
        sender_email: str,
        sender_name: str = "GrandFlow",
        timeout: float = 15.0,
        api_url: str | None = None,
        http: httpx.Client | None = None,
    ):
        super().__init__(sender_email, sender_name)
        # Overridable so local/dev can point this at a mock HTTP server
        # instead of the real Mailjet API.
        self.api_url = api_url or DEFAULT_MAILJET_API_URL
        self.http = (
            http if http is not None else httpx.Client(timeout=timeout, auth=(api_key, secret_key))
        )

    def send_template_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        template_id: str,
        personalization: dict,
    ) -> None:
        """Send via a Mailjet-hosted template (dashboard-managed body) —
        variable substitution is done by Mailjet from `personalization`,
        passed as flat `Variables` (Mailjet has no nested-object support)."""
        payload = {
            "Messages": [
                {
                    "From": {"Email": self.sender_email, "Name": self.sender_name},
                    "To": [{"Email": to_email, "Name": to_name or to_email}],
                    "Subject": subject,
                    "TemplateID": int(template_id),
                    "TemplateLanguage": True,
                    "Variables": personalization,
                }
            ]
        }
        try:
            resp = self.http.post(self.api_url, json=payload)
        except httpx.RequestError as exc:
            raise MailjetError(f"Could not reach Mailjet: {exc}", retryable=True) from exc

        if resp.status_code >= 400:
            raise MailjetError(
                f"Mailjet returned {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code,
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )
