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


def is_superuser(valid_user: dict) -> bool:
    return valid_user.get("role") == "superuser"


def require_donor(valid_user: dict) -> None:
    """Assert the caller's customer has is_donor=True.

    Mirrors services/budget/app/services/customer_client.py's require_donor —
    reads the flag straight off the decoded JWT payload rather than a DB
    lookup, since is_donor already travels in the token claims.
    """
    if not valid_user.get("is_donor"):
        raise DomainError("Customer is not a donor", status.HTTP_403_FORBIDDEN)


def _resolve_scoped_customer_id(
    valid_user: dict,
    explicit_id: UUID | None,
    *,
    field_name: str,
    require_donor_role: bool = False,
) -> UUID:
    """Resolve which customer_id a request acts as/on.

    A superuser has no donor/grantee customer of their own to derive from,
    so they must supply `explicit_id` (rejected if omitted). A regular
    caller is always scoped to their own `customer_id` JWT claim — anything
    they submit for `explicit_id` is ignored.
    """
    if is_superuser(valid_user):
        if explicit_id is None:
            raise DomainError(f"Superuser must specify {field_name}", status.HTTP_400_BAD_REQUEST)
        return explicit_id
    if require_donor_role:
        require_donor(valid_user)
    return UUID(str(valid_user["customer_id"]))


def create_donor_grantee_service(
    session: Session, valid_user: dict, grantee_id: UUID, donor_id: UUID | None = None
):
    donor_id = _resolve_scoped_customer_id(
        valid_user, donor_id, field_name="donor_id", require_donor_role=True
    )
    return create_donor_grantee(session, donor_id=donor_id, grantee_id=grantee_id)


def list_donor_grantees_service(
    session: Session, valid_user: dict, request_type: str | None, customer_id: UUID | None = None
):
    customer_id = _resolve_scoped_customer_id(valid_user, customer_id, field_name="customer_id")

    if request_type == "donor":
        return list_donor_grantees(session, donor_id=customer_id)
    if request_type == "grantee":
        return list_donor_grantees(session, grantee_id=customer_id)
    raise DomainError("request_type must be 'donor' or 'grantee'", status.HTTP_400_BAD_REQUEST)


def delete_donor_grantee_service(session: Session, valid_user: dict, donor_grantee_id: UUID):
    donor_grantee = get_donor_grantee(session, donor_grantee_id)
    if not donor_grantee:
        raise DomainError("Donor-grantee relationship not found", status.HTTP_404_NOT_FOUND)

    # A superuser may delete any relationship; a regular caller must be the
    # donor on the row itself (checked below), not merely *a* donor.
    if not is_superuser(valid_user):
        require_donor(valid_user)
        if str(donor_grantee.donor_id) != str(valid_user["customer_id"]):
            raise DomainError(
                "Cannot delete another donor's relationship", status.HTTP_403_FORBIDDEN
            )

    delete_donor_grantee(session, donor_grantee)
