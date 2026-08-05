from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.schemas.customer_schema import Customer
from app.db.session import get_db
from app.crud.customer_crud import (
    create_customer,
    get_customers,
    get_customer,
    get_customers_by_ids,
)
from app.utils.security import get_current_user
from uuid import UUID

router = APIRouter()


@router.get("/customers/", response_model=list[Customer])
def list_customers(
    is_ngo: bool | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    return get_customers(session=db, is_ngo=is_ngo, search=search)


@router.post("/customers/", response_model=Customer)
def create_customer_endpoint(
    customer: Customer,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    db_customer = create_customer(
        session=db,
        name=customer.name,
        is_ngo=customer.is_ngo,
        is_donor=customer.is_donor,
        country=customer.country,
        currency=customer.currency,
    )
    return db_customer


@router.get("/customers/{customer_id}", response_model=Customer)
def get_customer_endpoint(
    customer_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    customer = get_customer(session=db, customer_id=customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.post("/customers/by_ids/", response_model=list[Customer])
def get_customers_by_ids_endpoint(
    customer_ids: list[UUID],
    db: Session = Depends(get_db),
):
    # NOTE: internal service endpoint — no auth needed, caller must ensure authorization
    return get_customers_by_ids(session=db, customer_ids=customer_ids)
