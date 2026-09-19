from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from starlette.concurrency import run_in_threadpool
from .jwt_utils import decode_access_token
from .privileged_access import log_privileged_access
from .session_revocation import is_session_revoked
from .current_user_context import reset_current_user_id, set_current_user_id
from uuid import UUID
from jose import JWTError
from shared.observability import set_span_attributes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")  # Only valid in users service


async def get_current_user(token: str = Depends(oauth2_scheme)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
        role = payload.get("role")
        session_id = payload.get("session_id")

        if not user_id:
            raise ValueError("Missing user_id in token payload")

        # Safely convert to UUID
        try:
            user_uuid = UUID(user_id)
        except ValueError:
            raise ValueError("Invalid UUID format for user_id")

        # Enforced every request, not just issuance.
        if session_id and await is_session_revoked(session_id):
            raise ValueError("Session has been revoked")
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token is invalid or expired: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Must be a coroutine dependency, not `def` — a threadpool run gets its own context copy.
    token_ctx = set_current_user_id(user_uuid)
    try:
        yield {
            "user_id": user_uuid,
            "role": role,
            "token": token,
            "session_id": session_id,
            "payload": payload,
        }
    finally:
        reset_current_user_id(token_ctx)


async def get_validated_user(
    user: dict = Depends(get_current_user),
    request: Request = None,  # type: ignore[assignment]
) -> dict:
    """Full decoded JWT payload, reusing get_current_user's already-verified decode."""
    payload = dict(user["payload"])
    payload["token"] = user["token"]
    # Defense-in-depth; 403 (not 401) so clients know to verify, not re-login.
    if not payload.get("email_verified"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="email_not_verified",
        )
    set_span_attributes(user_id=payload.get("user_id"))
    if payload.get("is_impersonating"):
        # Offloaded to a thread — it's a blocking sync DB write.
        await run_in_threadpool(log_privileged_access, payload, request)
    return payload
