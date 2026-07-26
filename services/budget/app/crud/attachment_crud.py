from sqlalchemy.orm import Session
from app.models.report import AttachmentModel
from uuid import UUID


def create_attachment(
    session: Session,
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
    session.commit()
    session.refresh(attachment)
    return attachment


def get_attachment(session: Session, attachment_id: UUID) -> AttachmentModel | None:
    return session.query(AttachmentModel).filter(AttachmentModel.id == attachment_id).first()


def list_attachments(session: Session, report_line_id: UUID | None = None) -> list[AttachmentModel]:
    query = session.query(AttachmentModel)
    if report_line_id:
        query = query.filter(AttachmentModel.report_line_id == report_line_id)
    return query.all()


def delete_attachment(session: Session, attachment: AttachmentModel) -> bool:
    session.delete(attachment)
    session.commit()
    return True
