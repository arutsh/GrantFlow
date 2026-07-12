from uuid import uuid4

import factory


def make_valid_user(user_id=None, customer_id=None, role="user", token="testtoken"):
    """Returns a dict matching the structure of get_validated_user() output:
    the decoded JWT payload with an added 'token' key.

    Kept for existing tests; new tests should prefer ValidUserFactory.
    """
    return {
        "user_id": str(user_id or uuid4()),
        "customer_id": str(customer_id or uuid4()),
        "role": role,
        "token": token,
    }


class ValidUserFactory(factory.DictFactory):
    """Decoded-JWT-payload dict as produced by get_validated_user().

    Usage:
        ValidUserFactory()                                  # random user, random customer
        ValidUserFactory(role="superuser")                  # override any field
        ValidUserFactory.create_batch(2, customer_id=cid)   # two users, same tenant
    """

    user_id = factory.LazyFunction(lambda: str(uuid4()))
    customer_id = factory.LazyFunction(lambda: str(uuid4()))
    role = "user"
    token = "testtoken"
