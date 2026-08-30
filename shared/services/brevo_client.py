# /shared/services/brevo_client.py
import httpx

from shared.services.email_provider import EmailClient, EmailProviderError

DEFAULT_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class BrevoError(EmailProviderError):
    """Raised when the Brevo transactional email API can't be reached or rejects a send."""


class BrevoClient(EmailClient):
    """Thin wrapper around Brevo's transactional email API (v3); build once per process."""

    def __init__(
        self,
        api_key: str,
        sender_email: str,
        sender_name: str = "GrandFlow",
        timeout: float = 15.0,
        api_url: str | None = None,
        http: httpx.Client | None = None,
    ):
        super().__init__(sender_email, sender_name)
        # Overridable so local/dev can point this at a mock HTTP server
        # instead of the real Brevo API.
        self.api_url = api_url or DEFAULT_BREVO_API_URL
        self.http = (
            http
            if http is not None
            else httpx.Client(
                timeout=timeout,
                headers={"api-key": api_key, "Content-Type": "application/json"},
            )
        )

    def send_template_email(
        self,
        to_email: str,
        to_name: str,
        subject: str,
        template_id: str,
        personalization: dict,
    ) -> None:
        """Send via a Brevo-hosted template; personalization is passed as nested `params`."""
        payload = {
            "sender": {"email": self.sender_email, "name": self.sender_name},
            "to": [{"email": to_email, "name": to_name or to_email}],
            "subject": subject,
            "templateId": int(template_id),
            "params": personalization,
        }
        try:
            resp = self.http.post(self.api_url, json=payload)
        except httpx.RequestError as exc:
            raise BrevoError(f"Could not reach Brevo: {exc}", retryable=True) from exc

        if resp.status_code >= 400:
            raise BrevoError(
                f"Brevo returned {resp.status_code}: {resp.text[:300]}",
                status_code=resp.status_code,
                retryable=resp.status_code >= 500 or resp.status_code == 429,
            )
