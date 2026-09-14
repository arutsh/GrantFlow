from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.mapping import DonorTemplateModel


async def create_donor_template(
    session: AsyncSession,
    name: str,
    fingerprint: str | None = None,
    detected_structure: dict | None = None,
) -> DonorTemplateModel:
    """
    Create a donor template.
    """
    donor_template = DonorTemplateModel(
        name=name, fingerprint=fingerprint, detected_structure=detected_structure
    )
    session.add(donor_template)
    await session.commit()
    await session.refresh(donor_template)
    return donor_template


async def get_donor_template(session: AsyncSession, template_id: int) -> DonorTemplateModel | None:
    result = await session.execute(
        select(DonorTemplateModel).where(DonorTemplateModel.id == template_id)
    )
    return result.scalar_one_or_none()


async def list_donor_templates(session: AsyncSession, limit: int = 100):
    result = await session.execute(select(DonorTemplateModel).limit(limit))
    return list(result.scalars().all())


async def update_donor_template(
    session: AsyncSession, template_id: int, name: str
) -> DonorTemplateModel | None:
    existing_template = await get_donor_template(session, template_id)
    if not existing_template:
        return None
    existing_template.name = name
    await session.commit()
    await session.refresh(existing_template)
    return existing_template


async def delete_donor_template(session: AsyncSession, template_id: int) -> bool:
    template = await get_donor_template(session, template_id)
    if template:
        await session.delete(template)
        await session.commit()
        return True
    return False
