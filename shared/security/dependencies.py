from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from .jwt_utils import decode_access_token
from .privileged_access import log_privileged_access
from .session_revocation import is_session_revoked
from uuid import UUID
from jose import JWTError
from shared.observability import set_span_attributes

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")  # Only valid in users service


def get_current_user(token: str = Depends(oauth2_scheme)):
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

        # Checked on every request, not only at issuance — a logged-out or
        # admin-revoked session must stop working before its access token's
        # natural expiry (session-security spec: "Session Revocation
        # Enforced on Every Request").
        if session_id and is_session_revoked(session_id):
            raise ValueError("Session has been revoked")

        return {
            "user_id": user_uuid,
            "role": role,
            "token": token,
            "session_id": session_id,
            "payload": payload,
        }
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


def get_validated_user(
    user: dict = Depends(get_current_user),
    request: Request = None,  # type: ignore[assignment]
) -> dict:
    """Return the full decoded JWT payload, with the raw token attached.

    Reuses the payload `get_current_user` already decoded and verified —
    signature/expiry/revocation checks all already happened there, so this
    no longer re-decodes the token. Use this as a FastAPI dependency in
    every service instead of defining per-route copies.
    """
    payload = dict(user["payload"])
    payload["token"] = user["token"]
    set_span_attributes(user_id=payload.get("user_id"))
    if payload.get("is_impersonating"):
        log_privileged_access(payload, request)
    return payload
