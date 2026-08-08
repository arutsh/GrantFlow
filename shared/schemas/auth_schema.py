from uuid import UUID
from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterRequest(BaseModel):
    email: EmailStr
    first_name: Optional[str] = ""  # optional field
    last_name: Optional[str] = ""  # optional field
    password: str
    role: Optional[str] = "user"  # default value
    customer_id: Optional[UUID] = None  # optional field


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    status: str


class VerifyEmailRequest(BaseModel):
    email: EmailStr
    token: str


class VerifyEmailResponse(BaseModel):
    email_verified: bool


class ResendVerificationResponse(BaseModel):
    sent: bool
