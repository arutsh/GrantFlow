from pydantic import BaseModel, EmailStr, model_validator

from shared.security.password_policy import validate_password_strength


class InviteUserRequest(BaseModel):
    email: EmailStr
    first_name: str | None = ""
    last_name: str | None = ""
    role: str = "user"


class InviteUserResponse(BaseModel):
    user_id: str
    email: EmailStr
    status: str
    # Only populated when EXPOSE_VERIFICATION_TOKEN_FOR_TESTS is set — see
    # ResendVerificationResponse.debug_token for the same convention.
    debug_token: str | None = None


class AcceptInviteRequest(BaseModel):
    email: EmailStr
    token: str
    password: str

    @model_validator(mode="after")
    def _check_password_strength(self):
        validate_password_strength(self.password, email=self.email)
        return self


class AcceptInviteResponse(BaseModel):
    email_verified: bool


class RoleUpdateRequest(BaseModel):
    role: str


class CompanyUpdateRequest(BaseModel):
    name: str | None = None
    country: str | None = None
    currency: str | None = None
    is_ngo: bool | None = None
    is_donor: bool | None = None
