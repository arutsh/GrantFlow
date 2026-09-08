from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.donor_grantee_crud import donor_grantee_exists
from app.db.session import get_db
from app.schemas.donor_grantee_schema import DonorGrantee, DonorGranteeCreate
from app.services.donor_grantees_services import (
    create_donor_grantee_service,
    delete_donor_grantee_service,
    list_donor_grantees_service,
)
from shared.security.dependencies import get_validated_user

router = APIRouter()


@router.post("/donor-grantees/", response_model=DonorGrantee)
async def create_donor_grantee_endpoint(
    donor_grantee: DonorGranteeCreate,
    db: AsyncSession = Depends(get_db),
    valid_user: dict = Depends(get_validated_user),
):
    return await create_donor_grantee_service(
        db,
        valid_user,
        grantee_id=donor_grantee.grantee_id,
        donor_id=donor_grantee.donor_id,
    )


@router.get("/donor-grantees/", response_model=list[DonorGrantee])
async def list_donor_grantees_endpoint(
    request_type: str | None = None,
    customer_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
    valid_user: dict = Depends(get_validated_user),
):
    # customer_id is only honored for a superuser caller (see
    # list_donor_grantees_service) — a regular caller is always scoped to
    # their own customer_id regardless of what they pass here.
    return await list_donor_grantees_service(
        db, valid_user, request_type=request_type, customer_id=customer_id
    )


@router.delete("/donor-grantees/{donor_grantee_id}", status_code=204)
async def delete_donor_grantee_endpoint(
    donor_grantee_id: UUID,
    db: AsyncSession = Depends(get_db),
    valid_user: dict = Depends(get_validated_user),
):
    await delete_donor_grantee_service(db, valid_user, donor_grantee_id=donor_grantee_id)


@router.get("/donor-grantees/exists")
async def donor_grantee_exists_endpoint(
    donor_id: UUID,
    grantee_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    # NOTE: internal service endpoint — no auth needed, matching the existing
    # POST /customers/by_ids/ convention; caller must ensure authorization.
    return {"exists": await donor_grantee_exists(db, donor_id=donor_id, grantee_id=grantee_id)}
