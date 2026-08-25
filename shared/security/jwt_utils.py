import os
from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta, timezone
import uuid
from typing import Optional


def _load_secret_key() -> str:
    key = os.getenv("JWT_SECRET_KEY")
    if key:
        return key
    if os.getenv("ENV") == "production":
        raise RuntimeError("JWT_SECRET_KEY must be set when ENV=production")
    return "dev-only-insecure-secret-key"


SECRET_KEY = _load_secret_key()
ALGORITHM = "HS256"
# Short-lived by design (design.md decision 3): a stolen access token's
# exposure window is bounded to this TTL, with the refresh-token flow
# renewing access transparently. Env-configurable for ops flexibility.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "20"))
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Impersonation tokens: short expiry + the audit log is the mitigation, not revocation.
IMPERSONATION_TOKEN_EXPIRE_MINUTES = int(os.getenv("IMPERSONATION_TOKEN_EXPIRE_MINUTES", "15"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = {k: (str(v) if isinstance(v, uuid.UUID) else v) for k, v in data.items()}
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token():
    return str(uuid.uuid4())


def hash_token(token: str) -> str:
    return pwd_context.hash(token)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.JWTError:
        raise ValueError("Invalid token")


def verify_token_hash(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
