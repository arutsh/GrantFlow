import pytest

from shared.security.password_policy import validate_password_strength


class TestValidatePasswordStrength:
    def test_strong_password_accepted(self):
        validate_password_strength("Correct-Horse-1", email="a@b.com", name="Jane Doe")

    def test_too_short_rejected(self):
        with pytest.raises(ValueError, match="at least"):
            validate_password_strength("Ab1defg")

    def test_all_numeric_rejected(self):
        with pytest.raises(ValueError, match="numeric"):
            validate_password_strength("12345678")

    def test_same_as_email_rejected(self):
        with pytest.raises(ValueError, match="email"):
            validate_password_strength("user@example.com", email="user@example.com")

    def test_same_as_email_case_insensitive(self):
        with pytest.raises(ValueError, match="email"):
            validate_password_strength("USER@EXAMPLE.COM", email="user@example.com")

    def test_same_as_name_part_rejected(self):
        with pytest.raises(ValueError, match="name"):
            validate_password_strength("gandalfgrey", name="Gandalfgrey Doe")

    def test_full_name_with_space_rejected(self):
        with pytest.raises(ValueError, match="name"):
            validate_password_strength("John Smith", name="John Smith")

    def test_full_name_concatenated_without_space_rejected(self):
        # Neither "john" nor "smith" alone — only checking individual name
        # tokens would miss this.
        with pytest.raises(ValueError, match="name"):
            validate_password_strength("johnsmith", name="John Smith")

    def test_no_email_or_name_context_still_checks_length_and_numeric(self):
        validate_password_strength("a-strong-one")
        with pytest.raises(ValueError):
            validate_password_strength("87654321")
