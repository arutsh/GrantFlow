import io
from unittest.mock import MagicMock, patch

import pytest
from openpyxl import Workbook

from app.core.exceptions import DomainError
from app.models.budget import BudgetModel
from app.schemas.with_lines_schema import BudgetLineInput, CreateBudgetWithLinesRequest
from app.services.budget_services import (
    create_budget_with_lines_service,
    save_budget_as_template_service,
)
from app.services.excel_import_service import prepare_excel_import_service
from tests.factories.user import ValidUserFactory


def _workbook_bytes() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["1. Personnel", "", ""])
    ws.append(["", "Salaries", 5000])
    ws.append(["", "Travel", 200])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _upload_file(data: bytes, filename: str = "Donor_budget_template.xlsx") -> MagicMock:
    upload = MagicMock()
    upload.filename = filename
    upload.content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    upload.file = io.BytesIO(data)
    return upload


async def _import_fresh_budget(db, valid_user) -> dict:
    """Mirrors chat's /chat/import-excel orchestration for a fresh, unmatched import."""
    with patch("app.services.excel_import_service.storage_client.save"):
        prepared = await prepare_excel_import_service(
            db, valid_user, _upload_file(_workbook_bytes())
        )
    assert not prepared.matched

    request = CreateBudgetWithLinesRequest(
        budget_name="Imported Budget",
        external_funder_name="Imported budget",
        local_currency="EUR",
        lines=[
            BudgetLineInput(category_name="Personnel", description="Salaries", amount=5000.0),
            BudgetLineInput(category_name="Personnel", description="Travel", amount=200.0),
        ],
        excel_import_fingerprint=prepared.fingerprint,
        excel_import_structure={"category_col": 0, "description_col": 1, "amount_col": 2},
        excel_import_lines_locked_count=2,
    )
    return await create_budget_with_lines_service(request, valid_user, db)


@pytest.mark.anyio
class TestSaveAsTemplateEligibility:
    async def test_fresh_import_is_eligible(self, db):
        user = ValidUserFactory()
        created = await _import_fresh_budget(db, user)

        budget = db.get(BudgetModel, created["id"])
        assert budget.excel_import_fingerprint is not None
        assert budget.donor_template_id is None
        assert len(budget.lines) == budget.excel_import_lines_locked_count

    async def test_not_eligible_once_a_line_is_edited(self, db):
        user = ValidUserFactory()
        created = await _import_fresh_budget(db, user)
        budget = db.get(BudgetModel, created["id"])

        line = budget.lines[0]
        line.amount = 9999.0
        db.commit()

        with pytest.raises(DomainError) as exc_info:
            await save_budget_as_template_service(budget.id, "Acme Template", user, db)
        assert exc_info.value.status_code == 400

    async def test_not_eligible_for_a_manually_created_budget(self, db):
        from app.crud.budget_crud import create_budget

        user = ValidUserFactory()
        budget = create_budget(
            session=db,
            user_id=user["user_id"],
            name="Manual budget",
            funding_customer_id=None,
            external_funder_name="Some Funder",
            owner_id=user["customer_id"],
        )

        with pytest.raises(DomainError):
            await save_budget_as_template_service(budget.id, "Acme Template", user, db)


@pytest.mark.anyio
class TestSaveAsTemplate:
    async def test_creates_template_and_sets_donor_template_id(self, db):
        user = ValidUserFactory()
        created = await _import_fresh_budget(db, user)
        budget = db.get(BudgetModel, created["id"])
        fingerprint = budget.excel_import_fingerprint

        template = await save_budget_as_template_service(budget.id, "Acme Donor", user, db)

        assert template.name == "Acme Donor"
        assert template.fingerprint == fingerprint
        assert template.detected_structure["amount_col"] == 2

        db.refresh(budget)
        assert budget.donor_template_id == template.id

    async def test_subsequent_upload_with_same_fingerprint_is_matched(self, db):
        owner = ValidUserFactory()
        other_org = ValidUserFactory()

        created = await _import_fresh_budget(db, owner)
        budget = db.get(BudgetModel, created["id"])
        await save_budget_as_template_service(budget.id, "Acme Donor", owner, db)

        with patch("app.services.excel_import_service.storage_client.save"):
            second = await prepare_excel_import_service(
                db, other_org, _upload_file(_workbook_bytes())
            )

        assert second.matched is True
        assert second.donor_template_id is not None
        assert {line.description for line in second.lines} == {"Salaries", "Travel"}
