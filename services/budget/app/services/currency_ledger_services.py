from contextlib import contextmanager

from fastapi import status
from sqlalchemy import text
from uuid import UUID

from app.core.exceptions import DomainError, PermissionDenied
from app.crud.currency_conversion_crud import (
    FLOAT_EPSILON,
    create_allocation,
    create_currency_conversion,
    delete_allocations_for_report_line,
    get_currency_conversion,
    list_currency_conversions,
    list_unconsumed_lots,
    list_unsatisfied_report_lines,
    sum_report_line_amounts,
)
from app.crud.funding_receipt_crud import (
    create_funding_receipt,
    get_funding_receipt,
    list_funding_receipts,
)
from app.models.currency_ledger import CurrencyConversionModel
from app.models.report import ReportLineModel
from app.schemas.currency_ledger_schema import (
    CurrencyConversionCreate,
    FundingReceiptCreate,
    LedgerBalance,
)
from app.services.report_services import _get_report_or_404, get_viewable_budget, is_owner


@contextmanager
def budget_ledger_lock(db, budget_id: UUID):
    """Serializes ledger-mutating operations (recording a conversion, or
    creating/editing a report line — anything that reads unconsumed-lot or
    unsatisfied-expense balances and then writes allocation rows) for one
    budget, so two concurrent requests against the same budget can't both
    read the same balance and double-spend it. Different budgets are
    unaffected — only same-budget writes ever serialize.

    Uses a session-level Postgres advisory lock (`pg_advisory_lock`, not
    `pg_advisory_xact_lock`) acquired on a dedicated connection checked out
    directly from the engine's pool — deliberately NOT via `db`'s own
    transaction. Every crud function in this codebase commits immediately
    (`session.commit()` per call), so a lock tied to `db`'s transaction, or
    to whatever physical connection `db` happens to hold at any given
    moment, would be released or silently migrate to a different
    connection the instant the first nested crud call commits. A separate,
    held-open connection sidesteps that entirely.

    No-ops outside Postgres (e.g. the sqlite-backed unit test suite), where
    advisory locks don't exist and tests run single-threaded anyway."""
    engine = db.get_bind()
    if engine.dialect.name != "postgresql":
        yield
        return

    # pg_advisory_lock takes a signed bigint; UUID.int is a 128-bit unsigned
    # value, so fold it down to fit. Deterministic across processes — unlike
    # Python's hash(), which is randomized per-process for str/UUID.
    # str()-then-UUID() because GUID (shared/db/type_decorators.py) hands
    # back a plain str on Postgres but a real UUID on sqlite — coerce
    # either input shape the same way rather than assuming one.
    key = UUID(str(budget_id)).int & 0x7FFFFFFFFFFFFFFF
    with engine.connect() as conn:
        conn.execute(text("SELECT pg_advisory_lock(:key)"), {"key": key})
        try:
            yield
        finally:
            conn.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": key})


def _get_owned_budget(db, valid_user: dict, budget_id: UUID):
    budget = get_viewable_budget(db, valid_user, budget_id)
    if not is_owner(budget, valid_user):
        raise PermissionDenied()
    return budget


def _get_funding_receipt_or_404(db, receipt_id: UUID):
    receipt = get_funding_receipt(db, receipt_id)
    if not receipt:
        raise DomainError("Funding Receipt Not found", status.HTTP_400_BAD_REQUEST)
    return receipt


def _get_currency_conversion_or_404(db, conversion_id: UUID):
    conversion = get_currency_conversion(db, conversion_id)
    if not conversion:
        raise DomainError("Currency Conversion Not found", status.HTTP_400_BAD_REQUEST)
    return conversion


def record_receipt_service(db, valid_user: dict, receipt: FundingReceiptCreate):
    budget = _get_owned_budget(db, valid_user, receipt.budget_id)
    return create_funding_receipt(
        session=db,
        user_id=valid_user["user_id"],
        budget_id=budget.id,
        amount=receipt.amount,
        received_at=receipt.received_at,
    )


def get_funding_receipt_service(db, valid_user: dict, receipt_id: UUID):
    receipt = _get_funding_receipt_or_404(db, receipt_id)
    get_viewable_budget(db, valid_user, receipt.budget_id)
    return receipt


def list_funding_receipts_service(db, valid_user: dict, budget_id: UUID):
    # Owner or funder may view the ledger (matches the currency-ledger-ui
    # panel being visible to both) — only recording a receipt/conversion
    # stays owner-only, via _get_owned_budget below.
    get_viewable_budget(db, valid_user, budget_id)
    return list_funding_receipts(db, budget_id=budget_id)


def _consume_fifo(items, amount: float, create_row) -> None:
    """Walks `items` (an already oldest-first-ordered list of (entity,
    available_balance) pairs), greedily drawing down `amount` against each
    entity's balance in turn and calling create_row(entity, take) for every
    partial draw. Shared by allocate_fifo_service (one expense drawing from
    many conversion lots) and _backfill_unsatisfied_expenses (one new lot
    backfilling many outstanding expenses) — same algorithm, with the roles
    of consumer and pool reversed."""
    remaining = amount
    for entity, balance in items:
        if remaining <= FLOAT_EPSILON:
            break
        take = min(remaining, balance)
        create_row(entity, take)
        remaining -= take


def allocate_fifo_service(db, report_line: ReportLineModel) -> None:
    """Re-derives this report line's allocation from scratch: clears any
    existing allocation rows, then walks the budget's unconsumed conversion
    lots oldest-first, allocating the expense against them. Re-running this
    (safe to call after the line's amount changes, not just on creation) is
    what keeps allocations in sync with edits. Any remainder not covered by
    an existing lot is left unsatisfied (no allocation row) — the ledger
    balance is simply allowed to go negative until a later conversion
    backfills it (see record_conversion_service)."""
    delete_allocations_for_report_line(db, report_line.id)
    if report_line.amount is None:
        return

    report = _get_report_or_404(db, report_line.report_id)
    _consume_fifo(
        list_unconsumed_lots(db, report.budget_id),
        report_line.amount,
        lambda conversion, take: create_allocation(
            session=db,
            report_line_id=report_line.id,
            conversion_id=conversion.id,
            amount_allocated=take,
        ),
    )


def _backfill_unsatisfied_expenses(
    db, budget_id: UUID, conversion: CurrencyConversionModel
) -> None:
    """Before any of a newly recorded conversion's balance is available to
    new expenses, satisfy this budget's outstanding unsatisfied report-line
    expenses oldest-first — so a weekend petty-cash expense converted the
    following Monday still traces to that specific conversion."""
    _consume_fifo(
        list_unsatisfied_report_lines(db, budget_id),
        conversion.local_amount,
        lambda report_line, take: create_allocation(
            session=db,
            report_line_id=report_line.id,
            conversion_id=conversion.id,
            amount_allocated=take,
        ),
    )


def record_conversion_service(db, valid_user: dict, conversion: CurrencyConversionCreate):
    budget = _get_owned_budget(db, valid_user, conversion.budget_id)
    with budget_ledger_lock(db, budget.id):
        new_conversion = create_currency_conversion(
            session=db,
            user_id=valid_user["user_id"],
            budget_id=budget.id,
            donor_amount=conversion.donor_amount,
            local_amount=conversion.local_amount,
            converted_at=conversion.converted_at,
        )
        _backfill_unsatisfied_expenses(db, budget.id, new_conversion)
    return new_conversion


def get_currency_conversion_service(db, valid_user: dict, conversion_id: UUID):
    conversion = _get_currency_conversion_or_404(db, conversion_id)
    get_viewable_budget(db, valid_user, conversion.budget_id)
    return conversion


def list_currency_conversions_service(db, valid_user: dict, budget_id: UUID):
    get_viewable_budget(db, valid_user, budget_id)
    return list_currency_conversions(db, budget_id=budget_id)


def get_ledger_balance_service(db, valid_user: dict, budget_id: UUID) -> LedgerBalance:
    """Per-currency balances, never blended: the unconverted donor-currency
    balance (receipts not yet converted) and the unconsumed local-currency
    balance (converted funds not yet allocated to a report-line expense,
    which can be negative — see allocate_fifo_service). Owner or funder may
    read this, matching the other ledger read endpoints."""
    budget = get_viewable_budget(db, valid_user, budget_id)

    conversions = list_currency_conversions(db, budget_id=budget_id)
    donor_balance = sum(r.amount for r in list_funding_receipts(db, budget_id=budget_id)) - sum(
        c.donor_amount for c in conversions
    )
    local_balance = sum(c.local_amount for c in conversions) - sum_report_line_amounts(
        db, budget_id
    )

    return LedgerBalance(
        budget_id=budget.id,
        actual_currency=budget.actual_currency,
        donor_balance=donor_balance,
        local_currency=budget.local_currency,
        local_balance=local_balance,
    )
