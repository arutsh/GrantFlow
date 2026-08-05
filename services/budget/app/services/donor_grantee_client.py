import uuid

import requests

from app.core.config import settings
from app.core.exceptions import DomainError

DONOR_GRANTEE_SERVICE_URL = settings.donor_grantee_service_url


class DonorGranteeServiceError(Exception):
    pass


def check_donor_grantee_relationship(
    donor_id: str | uuid.UUID, grantee_id: str | uuid.UUID
) -> bool:
    """No caching, deliberately — unlike get_customer_cached, revocation must
    take effect on the very next call, not after some cache TTL/eviction."""
    try:
        resp = requests.get(
            f"{DONOR_GRANTEE_SERVICE_URL}exists",
            params={"donor_id": str(donor_id), "grantee_id": str(grantee_id)},
        )
        resp.raise_for_status()
        return bool(resp.json().get("exists", False))
    except requests.RequestException as e:
        raise DonorGranteeServiceError(
            f"Failed to check donor-grantee relationship for donor {donor_id}, "
            f"grantee {grantee_id}"
        ) from e


def validate_donor_grantee_relationship(
    donor_id: str | uuid.UUID,
    grantee_id: str | uuid.UUID,
    raise_domain_error: bool = False,
):
    """Assert a donor_grantees row exists linking donor_id (funder) to grantee_id (owner)."""
    Error = DomainError if raise_domain_error else ValueError
    try:
        exists = check_donor_grantee_relationship(donor_id, grantee_id)
    except DonorGranteeServiceError as e:
        raise Error(str(e))

    if not exists:
        raise Error(f"Donor {donor_id} has not approved grantee {grantee_id} to fund their budgets")
