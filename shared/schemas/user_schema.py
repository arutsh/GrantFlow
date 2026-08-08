from pydantic import BaseModel, EmailStr
from shared.schemas.customer_schema import Customer
import enum
from uuid import UUID


class UserStatus(str, enum.Enum):
    active = "active"
    pending = "pending"
    disabled = "disabled"


class UserRole(str, enum.Enum):
    superuser = "superuser"
    admin = "admin"
    user = "user"


class UserBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    role: UserRole
    customer_id: UUID | None = None
    status: UserStatus


class UserCreate(UserBase):
    class Config:
        extra = "ignore"  # 👈 Ignore unexpected fields like `id`


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    customer_id: UUID | None = None
    status: UserStatus | None = UserStatus.pending
    new_customer_name: str | None = None  # If creating a new customer


class User(UserBase):
    id: UUID
    customer: Customer | None = None
    email_verified: bool = False

    model_config = {"from_attributes": True}
