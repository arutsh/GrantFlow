from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app.schemas.mapping_schema import (
    DonorTemplateCreate,
    DonorTemplate,
)
from app.db.session import SessionLocal
from app.crud.budget_donor_template_crud import (
    create_donor_template,
    list_donor_templates,
)
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/donor-mapping", tags=["Donor Mapping"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Templates ---
@router.post("/templates", response_model=DonorTemplate)
def create_template(
    payload: DonorTemplateCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    created_template = create_donor_template(db, payload.name)
    set_span_attributes(donor_template_id=created_template.id)
    return created_template


@router.get("/templates", response_model=List[DonorTemplate])
def list_templates(db: Session = Depends(get_db), valid_user=Depends(get_validated_user)):
    return list_donor_templates(db)
