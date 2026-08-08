from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from zoneinfo import ZoneInfo

from app.schemas.auth_schema import (
    RegisterRequest,
    LoginRequest,
    TokenResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    ResendVerificationResponse,
)

from app.db.session import SessionLocal
from app.utils.security import (
    verify_password,
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_token_hash,
)
from app.crud.sessions_curd import create_session, get_session_by_id
from app.crud.user_crud import (
    get_user,
    get_user_by_email,
    create_user,
    set_email_verification_token,
    get_user_by_verification_token,
    mark_email_verified,
)
from app.crud.customer_crud import get_customer
from app.utils.redis import _cache_get, _delete_key
from app.services.celery_client import enqueue_verification_email
from shared.security.dependencies import get_validated_user
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _role_flags(customer) -> dict:
    """is_ngo/is_donor for the JWT, false when there is no customer."""
    if not customer:
        return {"is_ngo": False, "is_donor": False}
    return {"is_ngo": customer.is_ngo, "is_donor": customer.is_donor}


def _email_verified_claim(user) -> dict:
    """email_verified for the JWT, alongside the is_ngo/is_donor role flags."""
    return {"email_verified": bool(user.email_verified)}


def _customer_role_claims(db: Session, customer_id) -> dict:
    """Same as _role_flags, but for callers with only a customer_id, no
    already-loaded customer (e.g. a just-inserted user with nothing eager-
    loaded yet). Prefer passing the loaded customer via _role_flags directly
    when one is already in hand — UserModel.customer is lazy="joined", so
    it usually is.

    Swallows lookup failures instead of raising: callers of this reach it
    after already durably committing a user/session, so a transient DB
    error here should degrade the claims to false/false, not turn an
    already-successful registration into a 500 with no token issued.
    """
    if not customer_id:
        return {"is_ngo": False, "is_donor": False}
    try:
        customer = get_customer(db, customer_id)
    except Exception:
        logger.exception("Failed to look up customer %s for role claims", customer_id)
        return {"is_ngo": False, "is_donor": False}
    return _role_flags(customer)


@router.post("/register", response_model=TokenResponse)
async def register_endpoint(req: RegisterRequest, db: Session = Depends(get_db)):

    try:
        user = await create_user(
            session=db,
            email=req.email,
            password=req.password,
            first_name=req.first_name,
            last_name=req.last_name,
            role=req.role,
            customer_id=req.customer_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    raw_token = set_email_verification_token(db, user)
    try:
        enqueue_verification_email(user.email, raw_token, user.first_name)
    except Exception:
        # Registration already succeeded and was committed — a broker blip
        # shouldn't turn that into a failed registration response. The user
        # can self-serve via /auth/resend-verification either way.
        logger.exception("verification_email_enqueue_failed", user_id=str(user.id))

    refresh_token = create_refresh_token()
    session = create_session(
        session=db,
        user_id=user.id,
        refresh_token_hash=refresh_token,
    )

    token = create_access_token(
        {
            "user_id": user.id,
            "session_id": session.id,
            "role": user.role,
            "customer_id": user.customer_id,
            **_customer_role_claims(db, user.customer_id),
            **_email_verified_claim(user),
        }
    )

    return TokenResponse(access_token=token, refresh_token=refresh_token, status=user.status)


@router.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, req.email)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    refresh_token = create_refresh_token()

    session = create_session(
        session=db,
        user_id=user.id,
        refresh_token_hash=refresh_token,
    )

    token = create_access_token(
        {
            "user_id": user.id,
            "session_id": session.id,
            "role": user.role,
            "customer_id": user.customer_id,
            **_role_flags(user.customer),
            **_email_verified_claim(user),
        }
    )

    return TokenResponse(access_token=token, refresh_token=refresh_token, status=user.status)


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    redis_key = f"refresh:{refresh_token}"
    session_id = _cache_get(redis_key)
    _delete_key(redis_key)
    if not session_id:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    s = get_session_by_id(db, session_id)
    if not s:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    # Session model always has naive datetime, assume UTC
    if s.expires_at.replace(tzinfo=ZoneInfo("UTC")) < datetime.now(ZoneInfo("UTC")):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")

    if verify_token_hash(refresh_token, s.refresh_token_hash):
        # Rotate new refresh token
        new_refresh = create_refresh_token()
        s.refresh_token_hash = hash_token(new_refresh)
        db.commit()

        access_token = create_access_token(
            {
                "user_id": s.user_id,
                "session_id": s.id,
                "role": s.user.role,
                "customer_id": s.user.customer_id,
                **_role_flags(s.user.customer),
                **_email_verified_claim(s.user),
            }
        )

        return TokenResponse(
            access_token=access_token, refresh_token=new_refresh, status=s.user.status
        )

    raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@router.post("/auth/verify-email", response_model=VerifyEmailResponse)
def verify_email(req: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = get_user_by_verification_token(db, req.email, req.token)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    expires_at = user.email_verification_expires_at
    if not expires_at or expires_at.replace(tzinfo=ZoneInfo("UTC")) < datetime.now(ZoneInfo("UTC")):
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    mark_email_verified(db, user)
    return VerifyEmailResponse(email_verified=True)


@router.post("/auth/resend-verification", response_model=ResendVerificationResponse)
def resend_verification(
    current_user: dict = Depends(get_validated_user), db: Session = Depends(get_db)
):
    user = get_user(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.email_verified:
        return ResendVerificationResponse(sent=False)

    raw_token = set_email_verification_token(db, user)
    try:
        enqueue_verification_email(user.email, raw_token, user.first_name)
    except Exception:
        logger.exception("verification_email_enqueue_failed", user_id=str(user.id))

    return ResendVerificationResponse(sent=True)
