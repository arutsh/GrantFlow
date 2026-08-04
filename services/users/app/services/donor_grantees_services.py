from uuid import UUID

from fastapi import status
from sqlalchemy.orm import Session

from app.core.exceptions import DomainError
from app.core.logging import get_logger
from app.crud.donor_grantee_crud import (
    create_donor_grantee,
    delete_donor_grantee,
    get_donor_grantee,
    list_donor_grantees,
)

logger = get_logger(__name__)


def require_donor(valid_user: dict) -> None:
    """Assert the caller's customer has is_donor=True.

    Mirrors services/budget/app/services/customer_client.py's require_donor —
    reads the flag straight off the decoded JWT payload rather than a DB
    lookup, since is_donor already travels in the token claims.
    """
    if not valid_user.get("is_donor"):
        raise DomainError("Customer is not a donor", status.HTTP_403_FORBIDDEN)


def create_donor_grantee_service(
    session: Session, valid_user: dict, grantee_id: UUID, donor_id: UUID | None = None
):
    if valid_user.get("role") == "superuser":
        # Superusers aren't necessarily attached to a donor customer
        # themselves (see the analogous owner_id override in
        # budget_services.create_budget_service), so there's no JWT claim to
        # derive donor_id from — the caller must say which donor they mean.
        if donor_id is None:
            raise DomainError("Superuser must specify donor_id", status.HTTP_400_BAD_REQUEST)
    else:
        require_donor(valid_user)
        donor_id = UUID(str(valid_user["customer_id"]))

    return create_donor_grantee(session, donor_id=donor_id, grantee_id=grantee_id)


def list_donor_grantees_service(
    session: Session, valid_user: dict, role: str, customer_id: UUID | None = None
):
    if valid_user.get("role") == "superuser":
        # A superuser has no customer_id claim of their own to scope by —
        # they're asking on behalf of whichever customer they specify.
        if customer_id is None:
            raise DomainError("Superuser must specify customer_id", status.HTTP_400_BAD_REQUEST)
    else:
        customer_id = UUID(str(valid_user["customer_id"]))

    if role == "donor":
        return list_donor_grantees(session, donor_id=customer_id)
    if role == "grantee":
        return list_donor_grantees(session, grantee_id=customer_id)
    raise DomainError("role must be 'donor' or 'grantee'", status.HTTP_400_BAD_REQUEST)


def delete_donor_grantee_service(session: Session, valid_user: dict, donor_grantee_id: UUID):
    donor_grantee = get_donor_grantee(session, donor_grantee_id)
    if not donor_grantee:
        raise DomainError("Donor-grantee relationship not found", status.HTTP_404_NOT_FOUND)

    # A superuser may delete any relationship; a regular caller must be the
    # donor on the row itself (checked below), not merely *a* donor.
    if valid_user.get("role") != "superuser":
        require_donor(valid_user)
        if str(donor_grantee.donor_id) != str(valid_user["customer_id"]):
            raise DomainError(
                "Cannot delete another donor's relationship", status.HTTP_403_FORBIDDEN
            )

    delete_donor_grantee(session, donor_grantee)
