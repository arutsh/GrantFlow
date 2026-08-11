import pytest
from pydantic import ValidationError

from shared.schemas.auth_schema import RegisterRequest


def _valid_kwargs(**overrides):
    kwargs = dict(
        email="new@example.com",
        password="Correct-Horse-1",
        first_name="Jane",
        last_name="Doe",
        consent_data_processing=True,
    )
    kwargs.update(overrides)
    return kwargs


class TestRegisterRequestPasswordStrength:
    def test_strong_password_accepted(self):
        req = RegisterRequest(**_valid_kwargs())
        assert req.password == "Correct-Horse-1"

    def test_weak_password_rejected(self):
        with pytest.raises(ValidationError, match="at least"):
            RegisterRequest(**_valid_kwargs(password="short1"))

    def test_all_numeric_password_rejected(self):
        with pytest.raises(ValidationError, match="numeric"):
            RegisterRequest(**_valid_kwargs(password="12345678"))

    def test_password_matching_email_rejected(self):
        with pytest.raises(ValidationError, match="email"):
            RegisterRequest(**_valid_kwargs(email="dupe@example.com", password="dupe@example.com"))


class TestRegisterRequestConsent:
    def test_registration_without_consent_rejected(self):
        with pytest.raises(ValidationError, match="[Cc]onsent"):
            RegisterRequest(**_valid_kwargs(consent_data_processing=False))

    def test_registration_with_consent_accepted(self):
        req = RegisterRequest(**_valid_kwargs(consent_data_processing=True))
        assert req.consent_data_processing is True
        assert req.consent_marketing is False

    def test_marketing_consent_defaults_false_and_is_independent(self):
        req = RegisterRequest(**_valid_kwargs(consent_marketing=True))
        assert req.consent_marketing is True
