"""Route tests for /api/customers/ covering the auth + search-filter changes
made alongside ticket #191 (customer discovery filters, auth hardening).
"""

from tests.factories.user import CustomerFactory


def _persist(db, obj):
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


class TestListCustomers:
    def test_requires_auth(self, make_client, db):
        client = make_client(db=db)
        app = client.app
        from app.utils.security import get_current_user

        del app.dependency_overrides[get_current_user]

        response = client.get("/api/customers/")

        assert response.status_code == 401

    def test_search_escapes_ilike_wildcards(self, make_client, db):
        _persist(db, CustomerFactory.build(name="100% Match Org"))
        _persist(db, CustomerFactory.build(name="Unrelated Org"))
        client = make_client(db=db)

        response = client.get("/api/customers/", params={"search": "100%"})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "100% Match Org"

    def test_search_underscore_is_literal(self, make_client, db):
        _persist(db, CustomerFactory.build(name="a_b Org"))
        _persist(db, CustomerFactory.build(name="axb Org"))
        client = make_client(db=db)

        response = client.get("/api/customers/", params={"search": "a_b"})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "a_b Org"

    def test_is_ngo_filter(self, make_client, db):
        _persist(db, CustomerFactory.build(name="NGO Org", is_ngo=True))
        _persist(db, CustomerFactory.build(name="Donor Org", is_ngo=False))
        client = make_client(db=db)

        response = client.get("/api/customers/", params={"is_ngo": True})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "NGO Org"


class TestCreateCustomer:
    def test_requires_auth(self, make_client, db):
        client = make_client(db=db)
        app = client.app
        from app.utils.security import get_current_user

        del app.dependency_overrides[get_current_user]

        response = client.post(
            "/api/customers/",
            json={"name": "New Org", "country": "GB", "currency": "GBP"},
        )

        assert response.status_code == 401


class TestGetCustomer:
    def test_requires_auth(self, make_client, db):
        customer = _persist(db, CustomerFactory.build())
        client = make_client(db=db)
        app = client.app
        from app.utils.security import get_current_user
        from shared.security.dependencies import get_validated_user

        # get_validated_user's real implementation still delegates to
        # get_current_user for the actual decode, so both overrides need to
        # come off to exercise the unauthenticated path.
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_validated_user]

        response = client.get(f"/api/customers/{customer.id}")

        assert response.status_code == 401
