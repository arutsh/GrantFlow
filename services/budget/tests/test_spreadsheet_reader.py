import io

from openpyxl import Workbook

from app.services.template_detection.spreadsheet_reader import (
    ExcelStructureDetector,
    classify_row_label,
    to_extraction_grid,
)


def _workbook_bytes(rows: list[list]) -> bytes:
    wb = Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


class TestFilterOutFormulaRows:
    def test_keeps_row_and_blanks_only_the_formula_cell(self):
        """Regression test for the bug this change fixes: a row with a
        formula in one cell (e.g. a computed second-currency column) used to
        be dropped in its entirety, discarding the real amount alongside it."""
        data = _workbook_bytes([["Salaries", 5000, "=B1*8"]])
        reader = ExcelStructureDetector(io.BytesIO(data))
        reader.read_sheet_with_openpyxl()
        cleaned = reader.filter_out_formula_rows()

        body_row = cleaned.iloc[1]
        assert body_row[1] == "Salaries"
        assert body_row[2] == 5000
        assert body_row[3] is None  # only the formula cell is blanked


class TestFilterOutFormulaRowsWithCachedValue:
    def test_formula_cell_resolves_to_last_calculated_value(self):
        """Regression test for a real donor template (Mama Cash) where the
        local-currency column is itself computed as `=donor_col*rate` — the
        blank-to-None behavior discarded exactly the local-currency amount
        Group 5's dual-currency extraction needs. openpyxl only caches a
        formula's result if some spreadsheet application actually
        calculated it before save, so this test writes the cached value via
        the same mechanism (openpyxl doesn't evaluate formulas itself)."""
        data = _workbook_bytes([["Salaries", 5000, "=B1*8"]])
        reader = ExcelStructureDetector(io.BytesIO(data))
        # openpyxl's own writer never populates a cached formula result (it
        # has no calculation engine) — stub in the value a real spreadsheet
        # application would have cached on save, the way Excel/Sheets does.
        reader.ws_cached.cell(row=1, column=3).value = 40000
        reader.read_sheet_with_openpyxl()
        cleaned = reader.filter_out_formula_rows()

        body_row = cleaned.iloc[1]
        assert body_row[1] == "Salaries"
        assert body_row[2] == 5000
        assert body_row[3] == 40000  # resolved from the cached formula result


class TestFilterOutTotalRows:
    def test_excludes_category_total_and_grand_total_rows(self):
        data = _workbook_bytes(
            [
                ["Salaries", 5000],
                ["Total Personnel", 5000],
                ["Total Project", 5000],
            ]
        )
        reader = ExcelStructureDetector(io.BytesIO(data))
        df = reader.detect_structure()
        grid = to_extraction_grid(df)

        labels = [row[0] for row in grid]
        assert "Salaries" in labels
        assert "Total Personnel" not in labels
        assert "Total Project" not in labels

    def test_classify_row_label(self):
        assert classify_row_label("Total Personnel") == "category_total"
        assert classify_row_label("Total Project") == "grand_total"
        assert classify_row_label("Salaries") is None
        assert classify_row_label("") is None


class TestDetectStructurePreservesAmounts:
    def test_amounts_survive_the_extraction_pipeline(self):
        """detect_structure() must not blank out numeric cells — that's fine
        for the retired label-matching pipeline this class used to serve,
        but AI-first line extraction needs the actual amount values."""
        data = _workbook_bytes([["Salaries", 5000]])
        reader = ExcelStructureDetector(io.BytesIO(data))
        grid = to_extraction_grid(reader.detect_structure())

        assert grid == [["Salaries", "5000"]]
