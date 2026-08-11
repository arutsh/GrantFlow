from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import uuid4, UUID
from app.schemas.user_schema import User, UserCreate, UserUpdate
from app.schemas.consent_schema import ConsentState, ConsentUpdateRequest, EmailChangeRequest
from app.models.user import UserModel
from app.models.customer import CustomerModel
from app.db.session import SessionLocal
from app.utils.security import get_current_user
from app.crud.user_crud import (
    get_users_query,
    is_superuser,
    update_user,
    get_user,
    get_consent_state,
    set_marketing_consent,
    soft_delete_user,
    set_pending_email_verification_token,
    _publish_user_event,
)
from app.crud.customer_crud import create_customer, get_customer
from app.crud.sessions_curd import revoke_all_sessions_for_user
from app.services.budget_client import get_financial_record_refs
from app.services.celery_client import enqueue_verification_email
from shared.security.dependencies import get_validated_user
from shared.security.jwt_utils import REFRESH_TOKEN_EXPIRE_DAYS
from shared.security.session_revocation import mark_session_revoked
from app.utils.dict_tools import filter_dict_keys
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/users/", response_model=User)
async def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    if user.customer_id:
        customer = db.query(CustomerModel).filter(CustomerModel.id == user.customer_id).first()
        if not customer:
            raise HTTPException(status_code=400, detail="Invalid customer_id")

    db_user = UserModel(id=str(uuid4()), **user.model_dump())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    await _publish_user_event("user.created", db_user)

    return db_user


@router.get("/users/{user_id}", response_model=User)
def get_user_endpoint(user_id: str, db: Session = Depends(get_db)):
    user = db.query(UserModel).filter(UserModel.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/users/", response_model=list[User])
def list_users_endpoint(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Only superuser can list all users

    users = get_users_query(db)
    current_user = users.filter(UserModel.id == current_user["user_id"]).first()
    if current_user.role != "superuser":
        raise HTTPException(status_code=403, detail="Not authorized to list users")

    return users.all()


@router.post("/users/by_ids/", response_model=list[User])
def get_users_by_ids_endpoint(
    user_ids: list[UUID],
    db: Session = Depends(get_db),
):
    # NOTE: this end point is for internal service use only,
    # hence no need to check current_user permissions
    # calling service should ensure proper authorization

    return get_users_query(db, user_ids).all()


@router.patch("/users/{user_id}/", response_model=User)
async def update_user_endpoint(
    user_id: UUID,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    is_current_user_superuser = is_superuser(db, current_user["user_id"])

    if current_user["user_id"] != user_id and not is_current_user_superuser:
        raise HTTPException(status_code=403, detail="Not authorized to update this user")

    db_user = get_user(db, user_id)
    current_user = get_user(db, current_user["user_id"])
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    allowed_fields = set()
    if is_current_user_superuser:
        allowed_fields = {"first_name", "last_name", "email", "status", "customer_id", "role"}
    else:
        # Password changes go through POST /auth/change-password (requires
        # the current password + strength validation) — not this generic
        # PATCH, which has no way to verify the caller actually knows the
        # existing password.
        allowed_fields = {"first_name", "last_name", "status"}

    update_data = user_update.model_dump(exclude_unset=True)
    customer = None
    if (
        not is_current_user_superuser
        and user_update.new_customer_name
        and db_user.status == "pending"
    ):
        customer = create_customer(db, user_update.new_customer_name)
        update_data["status"] = "active"

    elif user_update.customer_id:
        customer = get_customer(session=db, customer_id=user_update.customer_id)
        if not customer:
            raise HTTPException(status_code=400, detail="Invalid customer_id")

    filtered_update_data = filter_dict_keys(update_data, allowed_fields)
    filtered_update_data["customer_id"] = customer.id if customer else None
    await update_user(db, db_user, filtered_update_data)

    return db_user


@router.get("/users/me/consent", response_model=ConsentState)
def get_my_consent(current_user: dict = Depends(get_validated_user), db: Session = Depends(get_db)):
    user = get_user(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return ConsentState(**get_consent_state(user))


@router.patch("/users/me/consent", response_model=ConsentState)
def update_my_consent(
    req: ConsentUpdateRequest,
    current_user: dict = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    user = get_user(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    set_marketing_consent(db, user, req.marketing)
    return ConsentState(**get_consent_state(user))


@router.get("/users/me/export")
async def export_my_data(
    current_user: dict = Depends(get_validated_user), db: Session = Depends(get_db)
):
    """Right to access (data-subject-rights spec): a downloadable, machine
    readable bundle of profile data, consent history, and a listing of the
    financial records the user created. Synchronous — orgs on this
    platform are small enough that this doesn't need async/email delivery
    (see design.md's open question; revisit if that stops being true)."""
    user = get_user(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    financial_records = await get_financial_record_refs(str(user.id), current_user["token"])

    return {
        "profile": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "status": user.status,
            "email_verified": user.email_verified,
        },
        "consent": get_consent_state(user),
        "financial_records_created": financial_records,
    }


@router.post("/users/me/email")
async def request_email_change(
    req: EmailChangeRequest,
    current_user: dict = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    """Rectification (data-subject-rights spec): the new address is stored
    unverified; the account keeps logging in with the old address until the
    verification link (same /auth/verify-email endpoint used at signup) is
    followed."""
    user = get_user(db, current_user["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.email_verified:
        # Otherwise this would overwrite the still-pending signup verification token.
        raise HTTPException(
            status_code=400,
            detail="Verify your current email address before requesting a change",
        )

    try:
        raw_token = set_pending_email_verification_token(db, user, req.new_email)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        enqueue_verification_email(req.new_email, raw_token, user.first_name)
    except Exception:
        logger.exception("email_change_verification_enqueue_failed", user_id=str(user.id))

    debug_token = raw_token if settings.EXPOSE_VERIFICATION_TOKEN_FOR_TESTS else None
    return {"pending_email": req.new_email, "debug_token": debug_token}


@router.delete("/users/{user_id}")
def delete_my_account(
    user_id: UUID,
    current_user: dict = Depends(get_validated_user),
    db: Session = Depends(get_db),
):
    """Right to erasure (data-subject-rights spec) — self-service only, no
    admin-initiated deletion of other accounts here."""
    if str(current_user["user_id"]) != str(user_id):
        raise HTTPException(status_code=403, detail="Not authorized to delete this account")

    user = get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    sessions = revoke_all_sessions_for_user(db, user_id)
    for s in sessions:
        mark_session_revoked(str(s.id), ttl_seconds=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600)

    soft_delete_user(db, user)
    return {"deleted": True}
