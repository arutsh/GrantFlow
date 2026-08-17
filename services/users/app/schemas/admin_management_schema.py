import pycountry
from pydantic import BaseModel, EmailStr, field_validator, model_validator

from shared.security.password_policy import validate_password_strength
from shared.services.currency_service import validate_currency


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

    @field_validator("country")
    @classmethod
    def _validate_country(cls, v):
        if v is None:
            return v
        if not pycountry.countries.get(alpha_2=v.upper()):
            raise ValueError(f"{v} is not a valid ISO Alpha-2 country code")
        return v.upper()

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v):
        if v is None:
            return v
        if not validate_currency(v):
            raise ValueError(f"{v} is not a valid ISO 4217 currency code")
        return v.upper()
