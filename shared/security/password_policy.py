MIN_PASSWORD_LENGTH = 8


def validate_password_strength(
    password: str, *, email: str | None = None, name: str | None = None
) -> None:
    """Raise ValueError with a user-facing message when `password` doesn't
    meet the minimum complexity bar. Shared by registration and
    password-change so both paths enforce the same policy (design.md
    decision 4).
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters long")

    if password.isdigit():
        raise ValueError("Password cannot be entirely numeric")

    lowered = password.strip().lower()
    if email and lowered == email.strip().lower():
        raise ValueError("Password cannot be the same as your email address")

    if name:
        name_parts = name.split()
        # Checks the full name (with and without spaces) in addition to
        # each individual token — a token-only check misses "JohnSmith" or
        # "John Smith" as a password for a user named John Smith, since
        # neither equals "john" or "smith" alone.
        candidates = {*("".join(name_parts).lower(), name.strip().lower())}
        candidates.update(part.lower() for part in name_parts if part)
        if lowered in candidates:
            raise ValueError("Password cannot be the same as your name")
