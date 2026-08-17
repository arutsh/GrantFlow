from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.customer import CustomerModel


def get_customer(session: Session, customer_id: UUID):
    return session.query(CustomerModel).filter(CustomerModel.id == customer_id).first()


def get_customers(
    session: Session,
    limit: int = 100,
    is_ngo: bool | None = None,
    search: str | None = None,
):
    query = session.query(CustomerModel)
    if is_ngo is not None:
        query = query.filter(CustomerModel.is_ngo == is_ngo)
    if search:
        # Escape ilike wildcards (% and _) in user input so they're matched
        # literally rather than acting as pattern metacharacters.
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.filter(CustomerModel.name.ilike(f"%{escaped}%", escape="\\"))
    return query.limit(limit).all()


def create_customer(
    session: Session,
    name: str,
    is_ngo: bool = False,
    is_donor: bool = False,
    country: str = "GB",
    currency: str = "GBP",
) -> CustomerModel:
    customer = CustomerModel(
        name=name,
        is_ngo=is_ngo,
        is_donor=is_donor,
        country=country,
        currency=currency,
    )
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


def get_customers_by_ids(session: Session, customer_ids: list[UUID]):
    return session.query(CustomerModel).filter(CustomerModel.id.in_(customer_ids)).all()


def update_customer(session: Session, customer: CustomerModel, updates: dict) -> CustomerModel:
    for key, value in updates.items():
        setattr(customer, key, value)
    session.commit()
    session.refresh(customer)
    return customer


def deactivate_customer(session: Session, customer: CustomerModel) -> CustomerModel:
    customer.deactivated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    session.commit()
    session.refresh(customer)
    return customer
