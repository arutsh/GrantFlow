"""
Tests for customer capability validation (P4).

validate_customer_can_fund  — customer must have is_donor=True
validate_customer_can_own   — customer must have is_ngo=True

Subgranting orgs (is_ngo=True, is_donor=True) must pass both checks.
"""
import pytest
from unittest.mock import patch
from uuid import uuid4

from app.services.customer_client import (
    validate_customer_can_fund,
    validate_customer_can_own,
    require_donor,
)
from app.core.exceptions import DomainError

CUSTOMER_ID = str(uuid4())


def _customer(is_ngo=False, is_donor=False):
    return {"id": CUSTOMER_ID, "name": "Test Org", "is_ngo": is_ngo, "is_donor": is_donor}


class TestValidateCustomerCanFund:
    def test_donor_passes(self):
        with patch(
            "app.services.customer_client.get_customer_cached",
            return_value=_customer(is_donor=True),
        ):
            result = validate_customer_can_fund(CUSTOMER_ID)
        assert result["is_donor"] is True

    def test_subgranting_ngo_passes(self):
        with patch(
            "app.services.customer_client.get_customer_cached",
            return_value=_customer(is_ngo=True, is_donor=True),
        ):
            result = validate_customer_can_fund(CUSTOMER_ID)
        assert result["is_donor"] is True

    def test_pure_ngo_raises_value_error(self):
        with patch(
            "app.services.customer_client.get_customer_cached",
            return_value=_customer(is_ngo=True, is_donor=False),
        ):
            with pytest.raises(ValueError):
                validate_customer_can_fund(CUSTOMER_ID)

    def test_pure_ngo_raises_domain_error_when_flagged(self):
        with patch(
            "app.services.customer_client.get_customer_cached",
            return_value=_customer(is_ngo=True, is_donor=False),
        ):
            with pytest.raises(DomainError):
                validate_customer_can_fund(CUSTOMER_ID, raise_domain_error=True)


class TestValidateCustomerCanOwn:
    def test_ngo_passes(self):
        with patch(
            "app.services.customer_client.get_customer_cached",
            return_value=_customer(is_ngo=True),
        ):
            result = validate_customer_can_own(CUSTOMER_ID)
        assert result["is_ngo"] is True

    def test_subgranting_ngo_passes(self):
        with patch(
            "app.services.customer_client.get_customer_cached",
            return_value=_customer(is_ngo=True, is_donor=True),
        ):
            result = validate_customer_can_own(CUSTOMER_ID)
        assert result["is_ngo"] is True

    def test_pure_donor_raises_value_error(self):
        with patch(
            "app.services.customer_client.get_customer_cached",
            return_value=_customer(is_ngo=False, is_donor=True),
        ):
            with pytest.raises(ValueError):
                validate_customer_can_own(CUSTOMER_ID)

    def test_pure_donor_raises_domain_error_when_flagged(self):
        with patch(
            "app.services.customer_client.get_customer_cached",
            return_value=_customer(is_ngo=False, is_donor=True),
        ):
            with pytest.raises(DomainError):
                validate_customer_can_own(CUSTOMER_ID, raise_domain_error=True)


class TestRequireDonor:
    """require_donor reads is_donor straight off the decoded JWT payload —
    no get_customer_cached call, unlike validate_customer_can_fund/can_own above."""

    def test_donor_passes(self):
        require_donor({"is_donor": True})  # does not raise

    def test_non_donor_raises_403(self):
        with pytest.raises(DomainError) as exc_info:
            require_donor({"is_donor": False})
        assert exc_info.value.status_code == 403

    def test_missing_is_donor_claim_raises_403(self):
        with pytest.raises(DomainError) as exc_info:
            require_donor({})
        assert exc_info.value.status_code == 403
