from sqlalchemy.orm import Session
from app.models.mapping import DonorTemplateModel


def create_donor_template(
    session: Session,
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
    session.commit()
    session.refresh(donor_template)
    return donor_template


def get_donor_template(session: Session, template_id: int) -> DonorTemplateModel | None:
    return session.query(DonorTemplateModel).filter(DonorTemplateModel.id == template_id).first()


def list_donor_templates(session: Session, limit: int = 100):
    return session.query(DonorTemplateModel).limit(limit).all()


def update_donor_template(
    session: Session, template_id: int, name: str
) -> DonorTemplateModel | None:
    existing_template = get_donor_template(session, template_id)
    if not existing_template:
        return None
    existing_template.name = name
    session.commit()
    session.refresh(existing_template)
    return existing_template


def delete_donor_template(session: Session, template_id: int) -> bool:
    template = get_donor_template(session, template_id)
    if template:
        session.delete(template)
        session.commit()
        return True
    return False
