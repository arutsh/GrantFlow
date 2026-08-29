from shared.services.console_email_client import ConsoleEmailClient
from shared.services.mailersend_client import MailerSendClient
from shared.services.mailjet_client import MailjetClient

# Shared by every tasks.users.send_*_email task — one client instance per
# provider per process, not per-call.
_client = None


def _build_mailersend_client(settings):
    return MailerSendClient(
        api_token=settings.MAILERSEND_API_TOKEN,
        sender_email=settings.MAILERSEND_SENDER_EMAIL,
        sender_name=settings.MAILERSEND_SENDER_NAME,
        api_url=settings.MAILERSEND_API_URL or None,
    )


def _build_mailjet_client(settings):
    return MailjetClient(
        api_key=settings.MAILJET_API_KEY,
        secret_key=settings.MAILJET_SECRET_KEY,
        sender_email=settings.MAILJET_SENDER_EMAIL,
        sender_name=settings.MAILJET_SENDER_NAME,
        api_url=settings.MAILJET_API_URL or None,
    )


def _build_console_client(settings):
    return ConsoleEmailClient()


_PROVIDER_BUILDERS = {
    "mailersend": _build_mailersend_client,
    "mailjet": _build_mailjet_client,
    "console": _build_console_client,
}


def get_email_client():
    global _client
    if _client is None:
        from config import settings

        # Falls back to console (not an error) when EMAIL_PROVIDER is unset/blank.
        provider = settings.EMAIL_PROVIDER or "console"
        builder = _PROVIDER_BUILDERS.get(provider)
        if builder is None:
            raise ValueError(
                f"Unsupported EMAIL_PROVIDER={provider!r}; "
                f"expected one of {sorted(_PROVIDER_BUILDERS)}"
            )
        _client = builder(settings)
    return _client
