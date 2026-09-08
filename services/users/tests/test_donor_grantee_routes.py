"""Route tests for /api/donor-grantees/ (ticket #189).

Uses a real in-memory sqlite session (the `db` fixture) rather than mocking
the crud/service layer, since the behavior under test — @validates hooks,
the unique constraint, JWT-role gating — only means something when it runs
against real model/DB behavior.
"""

import pytest

from app.crud.donor_grantee_crud import create_donor_grantee
from tests.factories.user import CustomerFactory


async def _persist(db, obj):
    db.add(obj)
    await db.commit()
    return obj


async def _make_donor(db, **kwargs):
    return await _persist(db, CustomerFactory.build(name="Donor Org", is_donor=True, **kwargs))


async def _make_grantee(db, **kwargs):
    return await _persist(db, CustomerFactory.build(name="Grantee Org", is_ngo=True, **kwargs))


@pytest.mark.anyio
class TestCreateDonorGrantee:
    async def test_donor_creates_relationship(self, make_client, db):
        donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        client = make_client(db=db, customer_id=str(donor.id), is_donor=True)

        response = client.post("/api/donor-grantees/", json={"grantee_id": str(grantee.id)})

        assert response.status_code == 200
        body = response.json()
        assert body["donor_id"] == str(donor.id)
        assert body["grantee_id"] == str(grantee.id)

    async def test_non_donor_create_is_rejected(self, make_client, db):
        grantee = await _make_grantee(db)
        client = make_client(db=db, is_donor=False)

        response = client.post("/api/donor-grantees/", json={"grantee_id": str(grantee.id)})

        assert response.status_code == 403

    async def test_create_against_non_ngo_target_is_rejected(self, make_client, db):
        donor = await _make_donor(db)
        non_ngo_target = await _persist(db, CustomerFactory.build(name="Not a grantee"))
        client = make_client(db=db, customer_id=str(donor.id), is_donor=True)

        response = client.post("/api/donor-grantees/", json={"grantee_id": str(non_ngo_target.id)})

        assert response.status_code == 400

    async def test_duplicate_create_is_rejected(self, make_client, db):
        donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        await create_donor_grantee(db, donor_id=donor.id, grantee_id=grantee.id)
        client = make_client(db=db, customer_id=str(donor.id), is_donor=True)

        response = client.post("/api/donor-grantees/", json={"grantee_id": str(grantee.id)})

        assert response.status_code == 400

    async def test_donor_id_is_always_the_caller_not_the_body(self, make_client, db):
        donor = await _make_donor(db)
        other_donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        client = make_client(db=db, customer_id=str(donor.id), is_donor=True)

        response = client.post(
            "/api/donor-grantees/",
            json={"grantee_id": str(grantee.id), "donor_id": str(other_donor.id)},
        )

        assert response.status_code == 200
        assert response.json()["donor_id"] == str(donor.id)

    async def test_superuser_can_specify_donor_id(self, make_client, db):
        donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        client = make_client(db=db, role="superuser")

        response = client.post(
            "/api/donor-grantees/",
            json={"grantee_id": str(grantee.id), "donor_id": str(donor.id)},
        )

        assert response.status_code == 200
        assert response.json()["donor_id"] == str(donor.id)

    async def test_superuser_without_donor_id_is_rejected(self, make_client, db):
        grantee = await _make_grantee(db)
        client = make_client(db=db, role="superuser")

        response = client.post("/api/donor-grantees/", json={"grantee_id": str(grantee.id)})

        assert response.status_code == 400


@pytest.mark.anyio
class TestListDonorGrantees:
    async def test_donor_lists_their_own_relationships(self, make_client, db):
        donor = await _make_donor(db)
        other_donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        other_grantee = await _make_grantee(db)
        await create_donor_grantee(db, donor_id=donor.id, grantee_id=grantee.id)
        await create_donor_grantee(db, donor_id=other_donor.id, grantee_id=other_grantee.id)
        client = make_client(db=db, customer_id=str(donor.id), is_donor=True)

        response = client.get("/api/donor-grantees/", params={"request_type": "donor"})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["donor_id"] == str(donor.id)

    async def test_grantee_lists_their_own_relationships(self, make_client, db):
        donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        other_grantee = await _make_grantee(db)
        await create_donor_grantee(db, donor_id=donor.id, grantee_id=grantee.id)
        await create_donor_grantee(db, donor_id=donor.id, grantee_id=other_grantee.id)
        client = make_client(db=db, customer_id=str(grantee.id), is_donor=False)

        response = client.get("/api/donor-grantees/", params={"request_type": "grantee"})

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["grantee_id"] == str(grantee.id)

    async def test_invalid_request_type_is_rejected(self, make_client, db):
        client = make_client(db=db, is_donor=True)

        response = client.get("/api/donor-grantees/", params={"request_type": "nope"})

        assert response.status_code == 400

    async def test_missing_request_type_is_400_not_422(self, make_client, db):
        client = make_client(db=db, is_donor=True)

        response = client.get("/api/donor-grantees/")

        assert response.status_code == 400

    async def test_superuser_lists_any_donors_relationships(self, make_client, db):
        donor = await _make_donor(db)
        other_donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        other_grantee = await _make_grantee(db)
        await create_donor_grantee(db, donor_id=donor.id, grantee_id=grantee.id)
        await create_donor_grantee(db, donor_id=other_donor.id, grantee_id=other_grantee.id)
        client = make_client(db=db, role="superuser")

        response = client.get(
            "/api/donor-grantees/", params={"request_type": "donor", "customer_id": str(donor.id)}
        )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["donor_id"] == str(donor.id)

    async def test_superuser_without_customer_id_is_rejected(self, make_client, db):
        client = make_client(db=db, role="superuser")

        response = client.get("/api/donor-grantees/", params={"request_type": "donor"})

        assert response.status_code == 400


@pytest.mark.anyio
class TestDeleteDonorGrantee:
    async def test_donor_deletes_their_own_relationship(self, make_client, db):
        donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        relationship = await create_donor_grantee(db, donor_id=donor.id, grantee_id=grantee.id)
        client = make_client(db=db, customer_id=str(donor.id), is_donor=True)

        response = client.delete(f"/api/donor-grantees/{relationship.id}")

        assert response.status_code == 204

    async def test_donor_cannot_delete_another_donors_relationship(self, make_client, db):
        donor = await _make_donor(db)
        other_donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        relationship = await create_donor_grantee(db, donor_id=donor.id, grantee_id=grantee.id)
        client = make_client(db=db, customer_id=str(other_donor.id), is_donor=True)

        response = client.delete(f"/api/donor-grantees/{relationship.id}")

        assert response.status_code == 403

    async def test_superuser_deletes_any_relationship(self, make_client, db):
        donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        relationship = await create_donor_grantee(db, donor_id=donor.id, grantee_id=grantee.id)
        client = make_client(db=db, role="superuser")

        response = client.delete(f"/api/donor-grantees/{relationship.id}")

        assert response.status_code == 204


@pytest.mark.anyio
class TestDonorGranteeExists:
    async def test_exists_returns_true(self, make_client, db):
        donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        await create_donor_grantee(db, donor_id=donor.id, grantee_id=grantee.id)
        client = make_client(db=db)

        response = client.get(
            "/api/donor-grantees/exists",
            params={"donor_id": str(donor.id), "grantee_id": str(grantee.id)},
        )

        assert response.status_code == 200
        assert response.json() == {"exists": True}

    async def test_exists_returns_false(self, make_client, db):
        donor = await _make_donor(db)
        grantee = await _make_grantee(db)
        client = make_client(db=db)

        response = client.get(
            "/api/donor-grantees/exists",
            params={"donor_id": str(donor.id), "grantee_id": str(grantee.id)},
        )

        assert response.status_code == 200
        assert response.json() == {"exists": False}
