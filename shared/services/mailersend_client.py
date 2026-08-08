# /shared/services/mailersend_client.py
import httpx

DEFAULT_MAILERSEND_API_URL = "https://api.mailersend.com/v1/email"


class MailerSendError(Exception):
    """Raised when the MailerSend Email API can't be reached or rejects a send."""


class MailerSendClient:
    """Thin wrapper around MailerSend's Email API (HTTPS), not SMTP — see
    the "MailerSend product" decision in the email-verification design doc.

    One client (and its underlying httpx client) is meant to be built once
    per process and reused across sends, not constructed per-call.
    """

    def __init__(
        self,
        api_token: str,
        sender_email: str,
        sender_name: str = "GrandFlow",
        timeout: float = 15.0,
        api_url: str | None = None,
        http: httpx.Client | None = None,
    ):
        self.sender_email = sender_email
        self.sender_name = sender_name
        # Overridable so local/dev can point this at a mock HTTP server
        # (e.g. WireMock) instead of the real MailerSend API.
        self.api_url = api_url or DEFAULT_MAILERSEND_API_URL
        self.http = (
            http
            if http is not None
            else httpx.Client(
                timeout=timeout,
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                },
            )
        )

    def send_template_email(
        self,
        to_email: str,
        subject: str,
        template_id: str,
        personalization: dict,
        to_name: str = "",
    ) -> None:
        """Send via a MailerSend-hosted template (dashboard-managed body)
        instead of inlining HTML/text in this codebase — variable
        substitution is done by MailerSend from `personalization`. MailerSend
        requires `subject` on every send regardless of template."""
        payload = {
            "from": {"email": self.sender_email, "name": self.sender_name},
            "to": [{"email": to_email, "name": to_name or to_email}],
            "subject": subject,
            "template_id": template_id,
            "personalization": [{"email": to_email, "data": personalization}],
        }
        try:
            resp = self.http.post(self.api_url, json=payload)
        except httpx.RequestError as exc:
            raise MailerSendError(f"Could not reach MailerSend: {exc}") from exc

        if resp.status_code >= 400:
            raise MailerSendError(f"MailerSend returned {resp.status_code}: {resp.text[:300]}")
