import factory
from uuid import uuid4

from shared.tests.factories.user import make_valid_user, ValidUserFactory  # noqa: F401
from shared.schemas.user_schema import UserRole, UserStatus
from app.models.user import UserModel
from app.models.customer import CustomerModel


class CustomerFactory(factory.Factory):
    class Meta:
        model = CustomerModel

    # str, not a raw UUID: create_access_token JSON-encodes this dict
    # directly, and matches what the GUID type decorator returns at
    # runtime anyway (see shared/db/type_decorators.py).
    id = factory.LazyFunction(lambda: str(uuid4()))
    name = factory.Faker("company")
    country = "GB"
    currency = "GBP"
    is_ngo = False
    is_donor = False


class UserModelFactory(factory.Factory):
    """A UserModel instance, built (not persisted) — matches the plain
    factory.Factory convention used for models elsewhere (see
    services/budget/tests/factories/budget.py).
    """

    class Meta:
        model = UserModel

    # str, not a raw UUID: create_access_token JSON-encodes this dict
    # directly, and matches what the GUID type decorator returns at
    # runtime anyway (see shared/db/type_decorators.py).
    id = factory.LazyFunction(lambda: str(uuid4()))
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.Faker("email")
    role = UserRole.user
    hashed_password = "hashed"
    customer_id = None
    status = UserStatus.pending
