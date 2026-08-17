"""Tests for POST /auth/impersonate. Calls the route function directly with a
mocked get_customer, matching test_auth_routes.py's convention."""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.auth_routes import start_impersonation
from app.schemas.auth_schema import ImpersonateRequest
from app.utils.security import decode_access_token
from tests.factories.user import CustomerFactory, ValidUserFactory


def _superuser(**kwargs):
    return ValidUserFactory(role="superuser", **kwargs)


class TestStartImpersonation:
    def test_superuser_can_mint_token_for_any_customer(self):
        customer = CustomerFactory.build()
        req = ImpersonateRequest(customer_id=customer.id)

        with patch("app.api.auth_routes.get_customer", return_value=customer):
            resp = start_impersonation(req, _superuser(), db=object())

        assert str(resp.customer_id) == customer.id
        assert resp.customer_name == customer.name

    def test_non_superuser_is_rejected(self):
        customer = CustomerFactory.build()
        req = ImpersonateRequest(customer_id=customer.id)

        with pytest.raises(HTTPException) as exc:
            start_impersonation(req, ValidUserFactory(role="admin"), db=object())

        assert exc.value.status_code == 403

    def test_unknown_customer_returns_404(self):
        req = ImpersonateRequest(customer_id=uuid4())

        with patch("app.api.auth_routes.get_customer", return_value=None):
            with pytest.raises(HTTPException) as exc:
                start_impersonation(req, _superuser(), db=object())

        assert exc.value.status_code == 404

    def test_token_is_scoped_to_target_customer_with_admin_equivalent_permissions(self):
        customer = CustomerFactory.build()
        req = ImpersonateRequest(customer_id=customer.id)

        with patch("app.api.auth_routes.get_customer", return_value=customer):
            resp = start_impersonation(req, _superuser(), db=object())

        claims = decode_access_token(resp.access_token)
        assert claims["customer_id"] == customer.id
        assert claims["role"] == "admin"
        assert claims["is_impersonating"] is True

    def test_token_carries_the_superusers_real_user_id(self):
        customer = CustomerFactory.build()
        req = ImpersonateRequest(customer_id=customer.id)
        superuser = _superuser()

        with patch("app.api.auth_routes.get_customer", return_value=customer):
            resp = start_impersonation(req, superuser, db=object())

        claims = decode_access_token(resp.access_token)
        assert claims["user_id"] == str(superuser["user_id"])

    def test_role_flags_reflect_the_target_customer_not_the_superuser(self):
        customer = CustomerFactory.build(is_ngo=True, is_donor=True)
        req = ImpersonateRequest(customer_id=customer.id)

        with patch("app.api.auth_routes.get_customer", return_value=customer):
            resp = start_impersonation(req, _superuser(), db=object())

        claims = decode_access_token(resp.access_token)
        assert claims["is_ngo"] is True
        assert claims["is_donor"] is True

    def test_expired_impersonation_token_is_rejected(self):
        customer = CustomerFactory.build()
        req = ImpersonateRequest(customer_id=customer.id)

        with (
            patch("app.api.auth_routes.get_customer", return_value=customer),
            patch("app.api.auth_routes.IMPERSONATION_TOKEN_EXPIRE_MINUTES", -1),
        ):
            resp = start_impersonation(req, _superuser(), db=object())

        with pytest.raises(ValueError, match="expired"):
            decode_access_token(resp.access_token)

    def test_mint_itself_is_audited(self):
        """get_validated_user's own audit hook never fires for this request."""
        customer = CustomerFactory.build()
        req = ImpersonateRequest(customer_id=customer.id)
        superuser = _superuser()
        fake_request = object()

        with (
            patch("app.api.auth_routes.get_customer", return_value=customer),
            patch("app.api.auth_routes.log_privileged_access") as mock_log,
        ):
            start_impersonation(req, superuser, db=object(), request=fake_request)

        mock_log.assert_called_once_with(
            {"user_id": str(superuser["user_id"]), "customer_id": str(customer.id)},
            fake_request,
        )
