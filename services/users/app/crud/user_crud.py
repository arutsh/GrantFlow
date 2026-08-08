import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID
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
) -> UserModel:
    existing = session.query(UserModel).filter(UserModel.email == email).first()
    if existing:
        logger.warning("user_creation_rejected", email=email, reason="email_already_exists")
        raise ValueError("Email already registered")

    user = UserModel(
        email=email,
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
        customer_id=customer_id,
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
    hash-verify, rather than scanning every account with a pending token."""
    user = get_user_by_email(session, email)
    if not user or not user.email_verification_token_hash:
        return None
    if not verify_token_hash(raw_token, user.email_verification_token_hash):
        return None
    return user


def mark_email_verified(session: Session, user: UserModel) -> UserModel:
    user.email_verified = True
    user.email_verification_token_hash = None
    user.email_verification_expires_at = None
    session.commit()
    session.refresh(user)
    return user
