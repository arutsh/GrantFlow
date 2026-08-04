from pydantic import BaseModel
from uuid import UUID


class DonorGrantee(BaseModel):
    id: UUID
    donor_id: UUID
    grantee_id: UUID

    model_config = {"from_attributes": True}


class DonorGranteeCreate(BaseModel):
    grantee_id: UUID
    # Only honored for a superuser caller — donor_id is otherwise always
    # derived from the caller's own customer_id claim (see require_donor in
    # donor_grantees_services.py). Ignored for a non-superuser caller.
    donor_id: UUID | None = None
