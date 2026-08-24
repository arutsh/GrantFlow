from unittest.mock import AsyncMock, patch

from app.schemas.excel_import_schema import ExcelPrepareImportResult


class TestPrepareExcelImportRoute:
    def test_uploads_file_and_returns_prepared_result(self, make_client):
        client = make_client()
        prepared = ExcelPrepareImportResult(matched=False, fingerprint="fp-1", rows=[["a"]])

        with patch(
            "app.api.budget_routes.prepare_excel_import_service",
            AsyncMock(return_value=prepared),
        ) as mock_prepare:
            resp = client.post(
                "/api/v1/budgets/excel/prepare-import",
                files={
                    "file": (
                        "budget.xlsx",
                        b"fake-bytes",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    )
                },
            )

        assert resp.status_code == 200
        assert resp.json() == prepared.model_dump()
        mock_prepare.assert_called_once()
        # db, valid_user, file — the uploaded file is the last positional arg
        uploaded_file = mock_prepare.call_args.args[-1]
        assert uploaded_file.filename == "budget.xlsx"

    def test_requires_authentication(self, make_client):
        client = make_client()
        client.app.dependency_overrides = {}
        resp = client.post(
            "/api/v1/budgets/excel/prepare-import",
            files={"file": ("budget.xlsx", b"fake-bytes", "application/octet-stream")},
        )
        assert resp.status_code == 401
