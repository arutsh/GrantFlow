from shared.security.dependencies import get_validated_user  # noqa: F401


def resolve_customer_id(valid_user: dict) -> str:
    """The tenant/billing identity for a request: customer_id, falling back to
    user_id for superusers, who aren't linked to a customer.
    """
    customer_id = valid_user.get("customer_id")
    return str(customer_id) if customer_id else str(valid_user["user_id"])
