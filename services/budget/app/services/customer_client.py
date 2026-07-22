import requests
from app.core.config import settings
from fastapi import status
from functools import lru_cache
import uuid
from app.core.exceptions import DomainError

CUSTOMER_SERVICE_URL = settings.customer_service_url


class CustomerServiceError(Exception):
    pass


def get_customer(customer_id: str | uuid.UUID) -> dict:
    try:
        resp = requests.get(f"{CUSTOMER_SERVICE_URL}{customer_id}")
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise CustomerServiceError(f"Failed to fetch customer {customer_id}") from e


@lru_cache(maxsize=128)
def get_customer_cached(customer_id: str | uuid.UUID) -> dict:
    return get_customer(customer_id)


def validate_customer_can_fund(customer_id: str | uuid.UUID, raise_domain_error: bool = False):
    """Assert the customer has is_donor=True (can issue grants)."""
    Error = DomainError if raise_domain_error else ValueError
    try:
        customer = get_customer_cached(customer_id)
    except CustomerServiceError as e:
        raise Error(str(e))

    if not customer.get("is_donor"):
        raise Error(f"Customer {customer_id} is not a donor and cannot fund budgets")
    return customer


def require_donor(valid_user: dict) -> None:
    """Assert the authenticated user's customer has is_donor=True.

    Reads the flag directly off the decoded JWT payload (get_validated_user's
    output) rather than calling get_customer_cached — that cache is unbounded
    with no TTL, and is_donor now travels in the token claims (ticket #135).
    """
    if not valid_user.get("is_donor"):
        raise DomainError("Customer is not a donor", status.HTTP_403_FORBIDDEN)


def validate_customer_can_own(customer_id: str | uuid.UUID, raise_domain_error: bool = False):
    """Assert the customer has is_ngo=True (can receive grants / own budgets)."""
    Error = DomainError if raise_domain_error else ValueError
    try:
        customer = get_customer_cached(customer_id)
    except CustomerServiceError as e:
        raise Error(str(e))

    if not customer.get("is_ngo"):
        raise Error(f"Customer {customer_id} is not an NGO and cannot own budgets")
    return customer
