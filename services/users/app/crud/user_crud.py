import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.user import UserModel
from app.utils.security import hash_password, hash_token, verify_token_hash
from app.services.event_publisher import get_publisher


from app.core.logging import get_logger

logger = get_logger(__name__)

EMAIL_VERIFICATION_TOKEN_TTL_HOURS = 24


def _user_event_payload(user: UserModel) -> dict:
    return {
        "user_id": str(user.id),
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "status": user.status,
        "customer_id": str(user.customer_id) if user.customer_id else None,
        "role": user.role,
    }


async def _publish_user_event(event_type: str, user: UserModel) -> None:
    try:
        publisher = get_publisher()
        await publisher.publish(event_type, _user_event_payload(user))
    except Exception as e:
        logger.error(
            "user_event_publish_failed", event_type=event_type, user_id=str(user.id), error=str(e)
        )


def get_user(session: Session, user_id: UUID):
    return session.query(UserModel).filter(UserModel.id == user_id).first()


def get_user_by_email(session: Session, email: str):
    return session.query(UserModel).filter(UserModel.email == email).first()


def is_superuser(session: Session, user_id: UUID) -> bool:
    user = get_user(session, user_id)
    return user is not None and user.role == "superuser"


def get_users_query(session: Session, user_ids: list[UUID] | None = None):
    query = session.query(UserModel)
    if user_ids:
        query = query.filter(UserModel.id.in_(user_ids))
    return query


def get_users_by_ids(session: Session, user_ids: list[UUID]):
    return get_users_query(session, user_ids).all()


def get_users(session: Session, limit: int = 100):
    return get_users_query(session).limit(limit).all()


async def create_user(
    session: Session,
    email: str,
    password: str,
    first_name: str | None = "",
    last_name: str | None = "",
    role: str | None = "user",
    customer_id: UUID | None = None,
    consent_data_processing: bool = False,
    consent_marketing: bool = False,
) -> UserModel:
    existing = session.query(UserModel).filter(UserModel.email == email).first()
    if existing:
        logger.warning("user_creation_rejected", email=email, reason="email_already_exists")
        raise ValueError("Email already registered")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user = UserModel(
        email=email,
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        customer_id=customer_id,
        # RegisterRequest already rejects consent_data_processing=False
        # (consent-management spec), so this is always set at this point —
        # still guarded here in case create_user is ever called directly.
        consent_data_processing_at=now if consent_data_processing else None,
        consent_marketing_at=now if consent_marketing else None,
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    logger.info(
        "user_created",
        user_id=str(user.id),
        email=user.email,
        role=role,
        customer_id=str(customer_id) if customer_id else None,
    )

    await _publish_user_event("user.created", user)
    return user


async def update_user(session: Session, user: UserModel, updates: dict) -> UserModel:
    for key, value in updates.items():
        if key == "password":
            value = hash_password(value)
        setattr(user, key, value)

    session.commit()
    session.refresh(user)

    await _publish_user_event("user.updated", user)
    return user


def get_user_customer_id(session: Session, user_id: UUID) -> UUID | None:
    user = get_user(session, user_id)
    if user:
        return user.customer_id
    return None


def set_email_verification_token(session: Session, user: UserModel) -> str:
    """Generate a new single-use verification token, store its hash +
    expiry on the user, and return the raw token — the raw value is only
    ever placed in the emailed link, never persisted itself. Overwrites any
    prior token, invalidating it (used for both initial send and resend)."""
    raw_token = secrets.token_urlsafe(32)
    user.email_verification_token_hash = hash_token(raw_token)
    user.email_verification_expires_at = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(hours=EMAIL_VERIFICATION_TOKEN_TTL_HOURS)
    session.commit()
    session.refresh(user)
    return raw_token


def get_user_by_verification_token(
    session: Session, email: str, raw_token: str
) -> UserModel | None:
    """The stored hash is bcrypt (salted), so equality can't be pushed into
    a WHERE clause — the caller supplies the email (round-tripped through
    the verification link) so lookup is a single indexed query + one
    hash-verify, rather than scanning every account with a pending token.

    Matches on `email` OR `pending_email` so this same lookup (and the same
    /auth/verify-email endpoint) serves both initial account verification
    and email-change rectification — the verification link always carries
    whichever address the token was actually issued for.
    """
    user = (
        session.query(UserModel)
        .filter(or_(UserModel.email == email, UserModel.pending_email == email))
        .first()
    )
    if not user or not user.email_verification_token_hash:
        return None
    if not verify_token_hash(raw_token, user.email_verification_token_hash):
        return None
    return user


def mark_email_verified(session: Session, user: UserModel) -> UserModel:
    user.email_verified = True
    if user.pending_email:
        # Rectification confirmation: promote the pending address now that
        # it's verified. The old address remained active/loginable up to
        # this point (data-subject-rights spec: "old email remains active
        # until confirmed").
        user.email = user.pending_email
        user.pending_email = None
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    session.commit()
    session.refresh(user)
    return user


def set_pending_email_verification_token(session: Session, user: UserModel, new_email: str) -> str:
    """Rectification: stores `new_email` as unverified and returns a raw
    verification token for it (mirrors set_email_verification_token). The
    account's active `email` is left untouched until the token is
    confirmed via /auth/verify-email."""
    existing = (
        session.query(UserModel)
        .filter(or_(UserModel.email == new_email, UserModel.pending_email == new_email))
        .first()
    )
    if existing and existing.id != user.id:
        # Covers both an already-active email and another user's in-flight
        # pending change to the same address — without the latter check,
        # both requests would succeed here and the second to actually
        # verify would hit the `email` unique constraint as an unhandled
        # 500 in /auth/verify-email instead of a clean error right here.
        raise ValueError("Email already registered")

    raw_token = secrets.token_urlsafe(32)
    user.pending_email = new_email
    user.email_verification_token_hash = hash_token(raw_token)
    user.email_verification_expires_at = datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(hours=EMAIL_VERIFICATION_TOKEN_TTL_HOURS)
    session.commit()
    session.refresh(user)
    return raw_token


def get_consent_state(user: UserModel) -> dict:
    return {
        "data_processing_granted": user.consent_data_processing_at is not None,
        "data_processing_at": user.consent_data_processing_at,
        "marketing_granted": user.consent_marketing_at is not None,
        "marketing_at": user.consent_marketing_at,
    }


def set_marketing_consent(session: Session, user: UserModel, granted: bool) -> UserModel:
    user.consent_marketing_at = datetime.now(timezone.utc).replace(tzinfo=None) if granted else None
    session.commit()
    session.refresh(user)
    return user


def _tombstone_email(user_id: UUID) -> str:
    return f"deleted-{user_id}@deleted.invalid"


def soft_delete_user(session: Session, user: UserModel) -> UserModel:
    """Right to erasure (data-subject-rights spec): scrub PII to a
    tombstone value and block future login, but keep the row — financial
    records' created_by/updated_by references must not dangle (design.md
    decision 2). Session revocation is the caller's job (it also needs to
    touch Redis — see app/api/auth_routes.py's _revoke_session_everywhere).
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    user.first_name = "Deleted"
    user.last_name = "User"
    user.email = _tombstone_email(user.id)
    user.pending_email = None
    user.hashed_password = None
    user.deletion_requested_at = user.deletion_requested_at or now
    user.deleted_at = now
    session.commit()
    session.refresh(user)
    return user
