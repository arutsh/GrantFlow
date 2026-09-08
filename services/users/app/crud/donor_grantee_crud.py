from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DomainError
from app.crud.customer_crud import get_customers_by_ids
from app.models.customer import DonorGranteeModel


async def create_donor_grantee(
    session: AsyncSession, donor_id: UUID, grantee_id: UUID
) -> DonorGranteeModel:
    if str(donor_id) == str(grantee_id):
        raise DomainError(
            "A customer cannot be its own donor and grantee", status.HTTP_400_BAD_REQUEST
        )

    # One query for both lookups. Keyed by str(id): CustomerModel.id round-trips
    # as either a str or a uuid.UUID depending on DB dialect (see GUID.process_result_value
    # in shared/db/type_decorators.py) — comparing as str sidesteps that mismatch.
    customers = {str(c.id): c for c in await get_customers_by_ids(session, [donor_id, grantee_id])}

    donor = customers.get(str(donor_id))
    if not donor:
        raise DomainError("Donor customer not found", status.HTTP_404_NOT_FOUND)

    grantee = customers.get(str(grantee_id))
    if not grantee:
        raise DomainError("Grantee customer not found", status.HTTP_404_NOT_FOUND)

    try:
        # Assigning donor/grantee (rather than donor_id/grantee_id) fires the
        # model's @validates hooks against the real customer objects.
        donor_grantee = DonorGranteeModel(donor=donor, grantee=grantee)
    except ValueError as e:
        raise DomainError(str(e), status.HTTP_400_BAD_REQUEST) from e

    session.add(donor_grantee)
    try:
        await session.commit()
    except IntegrityError as e:
        await session.rollback()
        raise DomainError(
            "This donor-grantee relationship already exists", status.HTTP_400_BAD_REQUEST
        ) from e
    return donor_grantee


async def list_donor_grantees(
    session: AsyncSession, *, donor_id: UUID | None = None, grantee_id: UUID | None = None
) -> list[DonorGranteeModel]:
    stmt = select(DonorGranteeModel)
    if donor_id is not None:
        stmt = stmt.where(DonorGranteeModel.donor_id == donor_id)
    if grantee_id is not None:
        stmt = stmt.where(DonorGranteeModel.grantee_id == grantee_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_donor_grantee(
    session: AsyncSession, donor_grantee_id: UUID
) -> DonorGranteeModel | None:
    result = await session.execute(
        select(DonorGranteeModel).where(DonorGranteeModel.id == donor_grantee_id)
    )
    return result.scalar_one_or_none()


async def delete_donor_grantee(session: AsyncSession, donor_grantee: DonorGranteeModel) -> None:
    await session.delete(donor_grantee)
    await session.commit()


async def donor_grantee_exists(session: AsyncSession, donor_id: UUID, grantee_id: UUID) -> bool:
    result = await session.execute(
        select(DonorGranteeModel).where(
            DonorGranteeModel.donor_id == donor_id,
            DonorGranteeModel.grantee_id == grantee_id,
        )
    )
    return result.scalar_one_or_none() is not None
