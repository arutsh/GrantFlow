import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Required env vars:
#   RABBITMQ_URL  — amqp://user:pass@host:5672//
#   REDIS_URL     — redis://host:6379/0
#   AI_DATABASE_URL — postgresql://user:pass@host:5432/grandflow_ai
#   EMAIL_PROVIDER — which transactional-email client to use: "console" (default — prints the
#                     send instead of calling an API, no credentials or network access needed),
#                     "mailersend", or "mailjet"
#   MAILERSEND_API_TOKEN    — MailerSend Email API token
#   MAILERSEND_SENDER_DOMAIN — trial domain in dev/staging, verified domain in prod
#   MAILERSEND_SENDER_EMAIL — from-address sent with each email (must belong to the sender domain)
#   MAILERSEND_VERIFICATION_TEMPLATE_ID — MailerSend dashboard template ID for the
#                                          verification email. Personalization vars: name,
#                                          verify_url, expiry_hours, support_email,
#                                          account_name, privacy_url
#   NOTE: privacy_url is sent to both providers, but only Mailjet's dashboard templates
#         render it — see DEPLOYMENT_MODES.md before making MailerSend primary again.
#   MAILERSEND_INVITE_TEMPLATE_ID — MailerSend dashboard template ID for the admin-invite
#                                    email (distinct from verification: welcomes the invitee,
#                                    names the inviter/company, links to /accept-invite).
#                                    Personalization vars: name, inviter_name, org_name,
#                                    invite_url, expiry_hours, support_email, privacy_url
#   MAILERSEND_PASSWORD_RESET_TEMPLATE_ID — MailerSend dashboard template ID for the
#                                            password-reset email. Personalization vars: name,
#                                            reset_url, expiry_hours, support_email,
#                                            account_name, privacy_url
#   MAILERSEND_API_URL — override for the MailerSend Email API endpoint; blank uses the real
#                         MailerSend API (only set this to point at a local mock in dev)
#   MAILJET_API_KEY / MAILJET_SECRET_KEY — Mailjet Send API v3.1 Basic Auth credentials
#   MAILJET_SENDER_EMAIL — from-address sent with each email (must belong to a verified sender)
#   MAILJET_VERIFICATION_TEMPLATE_ID — Mailjet dashboard template ID for the verification email
#   MAILJET_INVITE_TEMPLATE_ID — Mailjet dashboard template ID for the admin-invite email;
#                                 same personalization vars as MAILERSEND_INVITE_TEMPLATE_ID
#   MAILJET_PASSWORD_RESET_TEMPLATE_ID — Mailjet dashboard template ID for the password-reset
#                                         email; same personalization vars as
#                                         MAILERSEND_PASSWORD_RESET_TEMPLATE_ID
#   MAILJET_API_URL — override for the Mailjet Send API endpoint; blank uses the real Mailjet API
#                      (only set this to point at a local mock in dev)
#   BREVO_API_KEY — Brevo transactional email API key (header auth, no separate secret)
#   BREVO_SENDER_EMAIL — from-address sent with each email (must belong to a verified sender)
#   BREVO_VERIFICATION_TEMPLATE_ID — Brevo dashboard template ID for the verification email;
#                                     same personalization vars as
#                                     MAILERSEND_VERIFICATION_TEMPLATE_ID
#   BREVO_INVITE_TEMPLATE_ID — Brevo dashboard template ID for the admin-invite email;
#                               same personalization vars as MAILERSEND_INVITE_TEMPLATE_ID
#   BREVO_PASSWORD_RESET_TEMPLATE_ID — Brevo dashboard template ID for the password-reset email;
#                                       same personalization vars as
#                                       MAILERSEND_PASSWORD_RESET_TEMPLATE_ID
#   BREVO_API_URL — override for the Brevo API endpoint; blank uses the real Brevo API
#                    (only set this to point at a local mock in dev)
#   FRONTEND_BASE_URL — origin used to build the verification/accept-invite link,
#                        e.g. https://app.example.com

BASE_DIR = Path(__file__).resolve().parent
env_mode = os.getenv("ENV", "development")
if env_mode == "local":
    ENV_FILE = BASE_DIR / ".env.worker.local"
elif env_mode == "production":
    ENV_FILE = BASE_DIR / ".env.worker.prod"
elif env_mode == "test":
    ENV_FILE = BASE_DIR / ".env.worker.test"
else:
    ENV_FILE = BASE_DIR / ".env.worker.dev"


class Settings(BaseSettings):
    env: str = "development"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672//"
    REDIS_URL: str = "redis://localhost:6379/0"
    AI_DATABASE_URL: str
    EMAIL_PROVIDER: str = "console"
    MAILERSEND_API_TOKEN: str = ""
    MAILERSEND_SENDER_DOMAIN: str = ""
    MAILERSEND_SENDER_EMAIL: str = ""
    MAILERSEND_SENDER_NAME: str = "OpenGrandFlow"
    MAILERSEND_VERIFICATION_TEMPLATE_ID: str = ""
    MAILERSEND_INVITE_TEMPLATE_ID: str = ""
    MAILERSEND_PASSWORD_RESET_TEMPLATE_ID: str = ""
    MAILERSEND_API_URL: str = ""
    MAILJET_API_KEY: str = ""
    MAILJET_SECRET_KEY: str = ""
    MAILJET_SENDER_EMAIL: str = ""
    MAILJET_SENDER_NAME: str = "OpenGrandFlow"
    MAILJET_VERIFICATION_TEMPLATE_ID: str = ""
    MAILJET_INVITE_TEMPLATE_ID: str = ""
    MAILJET_PASSWORD_RESET_TEMPLATE_ID: str = ""
    MAILJET_API_URL: str = ""
    BREVO_API_KEY: str = ""
    BREVO_SENDER_EMAIL: str = ""
    BREVO_SENDER_NAME: str = "OpenGrandFlow"
    BREVO_VERIFICATION_TEMPLATE_ID: str = ""
    BREVO_INVITE_TEMPLATE_ID: str = ""
    BREVO_PASSWORD_RESET_TEMPLATE_ID: str = ""
    BREVO_API_URL: str = ""
    # So the {PROVIDER}_{PURPOSE}_TEMPLATE_ID getattr lookups resolve for EMAIL_PROVIDER=console.
    CONSOLE_VERIFICATION_TEMPLATE_ID: str = "console"
    CONSOLE_INVITE_TEMPLATE_ID: str = "console"
    CONSOLE_PASSWORD_RESET_TEMPLATE_ID: str = "console"
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=False, extra="ignore")


settings = Settings()  # type: ignore[call-arg]
