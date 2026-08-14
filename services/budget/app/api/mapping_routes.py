from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List

# from app.db.session import get_db
from app.schemas.mapping_schema import (
    DonorTemplateCreate,
    DonorTemplate,
    DonorFieldCreate,
    DonorField,
    MappingRequest,
    MappingResponse,
    MappingSuggestion,
    NgoMappingCreate,
    NgoMapping,
)
from app.models.mapping import (
    DonorFieldModel,
    NgoMappingModel,
)
from app.services.mapping_service import suggest_mapping
from app.db.session import SessionLocal
from app.crud.budget_donor_template_crud import (
    bulk_create_donor_fields,
    create_donor_template,
    get_donor_template,
    list_donor_templates,
    create_donor_field,
    list_donor_fields,
)
from app.schemas.budget_line_schema import BudgetCategoryCreate, BudgetCategory
from app.crud.budget_category_crud import create_budget_category, list_budget_categories
from app.services.mapping_service import suggest_semantic_mapping
from shared.observability import set_span_attributes
from shared.security.dependencies import get_validated_user  # noqa: F401

router = APIRouter(prefix="/donor-mapping", tags=["Donor Mapping"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_template_or_404(db: Session, template_id: int):
    template = get_donor_template(db, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    return template


@router.post("/ping")
def ping(db: Session = Depends(get_db), valid_user=Depends(get_validated_user)):
    from app.services.template_detection.spreadsheet_reader import ExcelStructureDetector

    file_path = "/app/uploads/Donor_budget_template.xlsx"
    # detected_structure = detect_excel_structure(file_path)
    # df = load_raw_sheet(file_path)
    excel_reader = ExcelStructureDetector(file_path)
    # Use the high-level pipeline to get a cleaned DataFrame
    df = excel_reader.detect_structure()

    # Serialize detections to JSON
    extracted_keywords = excel_reader.filter_list_of_possible_fields(df)
    suggested_mappings = suggest_semantic_mapping(extracted_keywords, db, valid_user)
    return suggested_mappings
    # return {"message": "pong"}


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


# --- Fields ---
@router.post("/fields", response_model=DonorField)
def create_field(
    payload: DonorFieldCreate, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(donor_template_id=payload.donor_template_id)
    _get_template_or_404(db, payload.donor_template_id)
    created_field = create_donor_field(db, payload.donor_template_id, payload.field_name)
    set_span_attributes(donor_field_id=created_field.id)
    return created_field


@router.post("/fields/bulk", response_model=List[DonorField])
def bulk_create_field_endpoint(
    template_id: int,
    field_names: List[str],
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(donor_template_id=template_id)
    _get_template_or_404(db, template_id)
    created_fields = bulk_create_donor_fields(db, template_id, field_names)
    set_span_attributes(donor_field_ids=",".join(str(f.id) for f in created_fields))
    return created_fields


@router.post("/categories", response_model=BudgetCategory)
def create_budget_category_endpoint(
    payload: BudgetCategoryCreate,
    db: Session = Depends(get_db),
    valid_user=Depends(get_validated_user),
):
    set_span_attributes(donor_template_id=payload.donor_template_id)
    if payload.donor_template_id is not None:
        _get_template_or_404(db, payload.donor_template_id)
    created_category = create_budget_category(
        db,
        user_id=valid_user["user_id"],
        name=payload.name,
        code=payload.code,
        donor_template_id=payload.donor_template_id,
    )
    set_span_attributes(budget_category_id=created_category.id)
    return created_category


@router.get("/categories", response_model=List[BudgetCategory])
def list_budget_categories_view(
    db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    return list_budget_categories(db)


@router.get("/categories/{template_id}", response_model=List[BudgetCategory])
def list_budget_categories_by_template(
    template_id: int, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(donor_template_id=template_id)
    return list_budget_categories(db, template_id)


@router.get("/fields/{template_id}", response_model=List[DonorField])
def list_fields(
    template_id: int, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(donor_template_id=template_id)
    return list_donor_fields(db, template_id)


# --- AI suggestions ---
@router.post("/suggest", response_model=MappingResponse)
def suggest(
    payload: MappingRequest, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    donor_fields = list(
        db.execute(
            select(DonorFieldModel.field_name).where(
                DonorFieldModel.donor_template_id == payload.donor_template_id
            )
        )
        .scalars()
        .all()
    )
    # donor_fields = [row[0] for row in donor_fields]
    suggestions = suggest_mapping(payload.ngo_fields, donor_fields)
    return MappingResponse(suggestions=[MappingSuggestion(**s) for s in suggestions])


# --- Persist mappings ---
@router.post("/mappings", response_model=NgoMapping)
def save_mapping(
    payload: NgoMappingCreate, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(donor_field_id=payload.donor_field_id)
    # Optionally verify donor_field_id exists:
    fld = db.get(DonorFieldModel, payload.donor_field_id)
    if not fld:
        raise HTTPException(404, "Donor field not found")

    m = NgoMappingModel(**payload.model_dump())
    db.add(m)
    db.commit()
    db.refresh(m)
    set_span_attributes(ngo_mapping_id=m.id)
    return m


@router.get("/mappings/by-ngo/{ngo_id}", response_model=List[NgoMapping])
def list_mappings(
    ngo_id: str, db: Session = Depends(get_db), valid_user=Depends(get_validated_user)
):
    set_span_attributes(ngo_id=ngo_id)
    return db.query(NgoMappingModel).filter(NgoMappingModel.ngo_id == ngo_id).all()
