"""Route tests for /api/customers/ covering the auth + search-filter changes
made alongside ticket #191 (customer discovery filters, auth hardening).
"""

import pytest

from tests.factories.user import CustomerFactory


async def _persist(db, obj):
    db.add(obj)
    await db.commit()
    return obj


@pytest.mark.anyio
class TestListCustomers:
    async def test_requires_auth(self, make_client, db):
        client = make_client(db=db)
        app = client.app
        from app.utils.security import get_current_user
        from shared.security.dependencies import get_validated_user

        # get_validated_user's real implementation still delegates to
        # get_current_user for the actual decode, so both overrides need to
        # come off to exercise the unauthenticated path.
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_validated_user]

        response = client.get("/api/customers/")

        assert response.status_code == 401

    async def test_search_escapes_ilike_wildcards(self, make_client, db):
        await _persist(db, CustomerFactory.build(name="100% Match Org"))
        await _persist(db, CustomerFactory.build(name="Unrelated Org"))
        client = make_client(db=db)

        response = client.get("/api/customers/", params={"search": "100%"})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "100% Match Org"

    async def test_search_underscore_is_literal(self, make_client, db):
        await _persist(db, CustomerFactory.build(name="a_b Org"))
        await _persist(db, CustomerFactory.build(name="axb Org"))
        client = make_client(db=db)

        response = client.get("/api/customers/", params={"search": "a_b"})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "a_b Org"

    async def test_is_ngo_filter(self, make_client, db):
        await _persist(db, CustomerFactory.build(name="NGO Org", is_ngo=True))
        await _persist(db, CustomerFactory.build(name="Donor Org", is_ngo=False))
        client = make_client(db=db)

        response = client.get("/api/customers/", params={"is_ngo": True})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["name"] == "NGO Org"


@pytest.mark.anyio
class TestCreateCustomer:
    async def test_requires_auth(self, make_client, db):
        client = make_client(db=db)
        app = client.app
        from app.utils.security import get_current_user
        from shared.security.dependencies import get_validated_user

        # get_validated_user's real implementation still delegates to
        # get_current_user for the actual decode, so both overrides need to
        # come off to exercise the unauthenticated path.
        del app.dependency_overrides[get_current_user]
        del app.dependency_overrides[get_validated_user]

        response = client.post(
            "/api/customers/",
            json={"name": "New Org", "country": "GB", "currency": "GBP"},
        )

        assert response.status_code == 401

    async def test_respects_explicit_is_ngo_false(self, make_client, db):
        client = make_client(db=db)

        response = client.post(
            "/api/customers/",
            json={
                "name": "Donor Org",
                "country": "GB",
                "currency": "GBP",
                "is_ngo": False,
            },
        )

        assert response.status_code == 200
        assert response.json()["is_ngo"] is False


@pytest.mark.anyio
class TestGetCustomer:
    async def test_requires_auth(self, make_client, db):
        customer = await _persist(db, CustomerFactory.build())
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
