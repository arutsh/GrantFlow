from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.report import AttachmentModel
from uuid import UUID


async def create_attachment(
    session: AsyncSession,
    user_id: UUID,
    report_line_id: UUID,
    filename: str,
    content_type: str,
    size: int,
    storage_key: str,
) -> AttachmentModel:
    attachment = AttachmentModel(
        report_line_id=report_line_id,
        filename=filename,
        content_type=content_type,
        size=size,
        storage_key=storage_key,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(attachment)
    await session.commit()
    return attachment


async def get_attachment(session: AsyncSession, attachment_id: UUID) -> AttachmentModel | None:
    result = await session.execute(
        select(AttachmentModel).where(AttachmentModel.id == attachment_id)
    )
    return result.scalar_one_or_none()


async def list_attachments(
    session: AsyncSession, report_line_id: UUID | None = None
) -> list[AttachmentModel]:
    query = select(AttachmentModel)
    if report_line_id:
        query = query.where(AttachmentModel.report_line_id == report_line_id)
    result = await session.execute(query)
    return list(result.scalars().all())


async def delete_attachment(session: AsyncSession, attachment: AttachmentModel) -> bool:
    await session.delete(attachment)
    await session.commit()
    return True
