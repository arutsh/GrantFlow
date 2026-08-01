import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import Modal from "@/components/ui/Modal";
import { SummaryStat } from "./BudgetViewSummary";
import { formatCurrency } from "@/utils/currency";
import { formatDateOnly } from "@/utils/datetime";
import { getCurrentCustomerId, isBudgetFunder, isBudgetOwner } from "@/utils/roleAccess";
import {
  createFundingReceipt,
  listFundingReceiptsByBudget,
  createCurrencyConversion,
  listCurrencyConversionsByBudget,
  getLedgerBalance,
} from "@/api/currencyLedgerApi";
import {
  fundingReceiptsQueryKey,
  currencyConversionsQueryKey,
  ledgerBalanceQueryKey,
} from "../queryKeys";
import { Budget, FundingReceipt, CurrencyConversion } from "../types/budget";

function impliedRate(conversion: CurrencyConversion): string {
  const { donor_amount, local_amount } = conversion;
  if (!donor_amount || !local_amount) return "—";
  return (donor_amount / local_amount).toFixed(4);
}

type HistoryEntry =
  | { kind: "receipt"; date: string; item: FundingReceipt }
  | { kind: "conversion"; date: string; item: CurrencyConversion };

export function CurrencyLedgerPanel({
  budget,
  onRequestEditActualCurrency,
}: {
  budget: Budget;
  onRequestEditActualCurrency?: () => void;
}) {
  const currentCustomerId = getCurrentCustomerId();
  const owner = isBudgetOwner(budget, currentCustomerId);
  const funder = isBudgetFunder(budget, currentCustomerId);
  const hasActualCurrency = !!budget.actual_currency;
  // A draft budget has nothing to reconcile yet — funding only makes sense
  // once the budget's committed. Unlike ReportsList (which also shows once
  // historical reports exist, to survive a later revert-to-draft/archive),
  // this doesn't check for existing ledger entries: recording a receipt/
  // conversion isn't gated by confirmation on the backend, so entries can
  // in principle exist on a since-reverted budget — deliberately kept
  // simple for now rather than mirroring that edge case unasked.
  const isConfirmed = budget.status === "confirmed";
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false);
  const [isConversionModalOpen, setIsConversionModalOpen] = useState(false);

  // Hooks always run (Rules of Hooks) — visibility is decided below, after
  // they're called, same as ReportsList's shouldShow pattern.
  const canView = owner || funder;
  const receiptsQuery = useQuery({
    queryKey: fundingReceiptsQueryKey(budget.id),
    queryFn: () => listFundingReceiptsByBudget(budget.id),
    enabled: canView && isConfirmed && hasActualCurrency,
  });
  const conversionsQuery = useQuery({
    queryKey: currencyConversionsQueryKey(budget.id),
    queryFn: () => listCurrencyConversionsByBudget(budget.id),
    enabled: canView && isConfirmed && hasActualCurrency,
  });
  const balanceQuery = useQuery({
    queryKey: ledgerBalanceQueryKey(budget.id),
    queryFn: () => getLedgerBalance(budget.id),
    enabled: canView && isConfirmed && hasActualCurrency,
  });

  // Owner or funder may view the ledger, matching the backend's read
  // endpoints — recording a receipt/conversion, and setting the actual
  // currency, stay owner-only below. Confirmed-only, per the user's
  // 2026-07-31 dogfooding feedback.
  if (!canView || !isConfirmed) return null;

  if (!hasActualCurrency) {
    return (
      <Card className="w-full bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
        <CardHeader>
          <h2 className="text-section-title">Currency Ledger</h2>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-500">
            {owner
              ? "Set this budget's actual (donor-transfer) currency to start recording funding receipts and conversions."
              : "The grantee hasn't set this budget's actual (donor-transfer) currency yet."}
          </p>
          {owner && (
            <Button
              variant="secondary"
              className="mt-3 text-sm"
              onClick={onRequestEditActualCurrency}
            >
              Set Actual Currency
            </Button>
          )}
        </CardContent>
      </Card>
    );
  }

  const receipts = receiptsQuery.data ?? [];
  const conversions = conversionsQuery.data ?? [];
  const balance = balanceQuery.data;

  const receivedToDate = receipts.reduce((sum, r) => sum + (r.amount ?? 0), 0);
  const sameCurrency = budget.local_currency === budget.actual_currency;
  const totalAmount = budget.total_amount ?? 0;
  const receivedPct =
    sameCurrency && totalAmount > 0 ? Math.round((receivedToDate / totalAmount) * 100) : 0;

  // Newest first, same convention as a bank/ledger statement.
  const history: HistoryEntry[] = [
    ...receipts.map((r) => ({ kind: "receipt" as const, date: r.received_at ?? "", item: r })),
    ...conversions.map((c) => ({
      kind: "conversion" as const,
      date: c.converted_at ?? "",
      item: c,
    })),
  ].sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));

  return (
    <Card className="w-full bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
          <h2 className="text-section-title">Currency Ledger</h2>
          {owner && (
            <div className="flex flex-wrap gap-2 sm:flex-nowrap">
              <Button
                variant="primary"
                className="text-sm w-full sm:w-auto"
                onClick={() => setIsReceiptModalOpen(true)}
              >
                + Record Payment Received
              </Button>
              <Button
                variant="secondary"
                className="text-sm w-full sm:w-auto"
                onClick={() => setIsConversionModalOpen(true)}
              >
                + Record Conversion
              </Button>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-4 mb-4">
          {balance && (
            <>
              <SummaryStat
                label={`Unconverted (${balance.actual_currency ?? budget.actual_currency})`}
                value={formatCurrency(balance.donor_balance, balance.actual_currency ?? undefined)}
              />
              <SummaryStat
                label={`Unconsumed (${balance.local_currency ?? budget.local_currency})`}
                value={formatCurrency(balance.local_balance, balance.local_currency ?? undefined)}
              />
            </>
          )}
          {sameCurrency ? (
            <SummaryStat
              label="Received to Date"
              value={formatCurrency(receivedToDate, budget.actual_currency)}
              sub={`${receivedPct}% of ${formatCurrency(totalAmount, budget.local_currency)}`}
            />
          ) : (
            <>
              <SummaryStat
                label="Received to Date"
                value={formatCurrency(receivedToDate, budget.actual_currency)}
              />
              <SummaryStat
                label="Budget Total"
                value={formatCurrency(totalAmount, budget.local_currency)}
              />
            </>
          )}
        </div>

        <div className="pt-4 border-t border-dashed border-slate-200">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-2">
            History
          </h3>
          {history.length === 0 ? (
            <p className="text-sm text-slate-500">
              No funding receipts or conversions recorded yet.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100">
              {history.map((entry) => (
                <li
                  key={`${entry.kind}-${entry.item.id}`}
                  className="py-2 flex flex-wrap items-center justify-between gap-3 text-sm"
                >
                  {entry.kind === "receipt" ? (
                    <>
                      <span className="text-slate-700 font-medium">Funding receipt</span>
                      <span className="text-slate-600">
                        {formatCurrency(entry.item.amount ?? 0, budget.actual_currency)}
                      </span>
                      <span className="text-slate-400 text-xs">
                        {formatDateOnly(entry.date) ?? "—"}
                      </span>
                    </>
                  ) : (
                    <>
                      <span className="text-slate-700 font-medium">Conversion</span>
                      <span className="text-slate-600">
                        {formatCurrency(
                          (entry.item as CurrencyConversion).donor_amount ?? 0,
                          budget.actual_currency
                        )}
                        {" → "}
                        {formatCurrency(
                          (entry.item as CurrencyConversion).local_amount ?? 0,
                          budget.local_currency
                        )}
                      </span>
                      <span className="text-slate-400 text-xs">
                        rate {impliedRate(entry.item as CurrencyConversion)} ·{" "}
                        {formatDateOnly(entry.date) ?? "—"}
                      </span>
                    </>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>
      </CardContent>

      {isReceiptModalOpen && (
        <RecordFundingReceiptModal
          budget={budget}
          isOpen={isReceiptModalOpen}
          onClose={() => setIsReceiptModalOpen(false)}
        />
      )}
      {isConversionModalOpen && (
        <RecordCurrencyConversionModal
          budget={budget}
          isOpen={isConversionModalOpen}
          onClose={() => setIsConversionModalOpen(false)}
        />
      )}
    </Card>
  );
}

function RecordFundingReceiptModal({
  budget,
  isOpen,
  onClose,
}: {
  budget: Budget;
  isOpen: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [amount, setAmount] = useState("");
  const [receivedAt, setReceivedAt] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setError("");
    try {
      await createFundingReceipt({
        budget_id: budget.id,
        amount: Number(amount),
        received_at: receivedAt,
      });
      queryClient.invalidateQueries({ queryKey: fundingReceiptsQueryKey(budget.id) });
      queryClient.invalidateQueries({ queryKey: ledgerBalanceQueryKey(budget.id) });
      onClose();
    } catch {
      setError("Failed to record funding receipt. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Record Payment Received">
      <form onSubmit={handleSubmit} className="flex flex-col">
        <Input
          label={`Amount (${budget.actual_currency})`}
          name="receipt_amount"
          type="number"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          disabled={isSaving}
          required
        />
        <Input
          label="Received Date"
          name="receipt_received_at"
          type="date"
          value={receivedAt}
          onChange={(e) => setReceivedAt(e.target.value)}
          disabled={isSaving}
          required
        />
        {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSaving || !amount || !receivedAt}>
            {isSaving ? "Saving..." : "Record Receipt"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function RecordCurrencyConversionModal({
  budget,
  isOpen,
  onClose,
}: {
  budget: Budget;
  isOpen: boolean;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [donorAmount, setDonorAmount] = useState("");
  const [localAmount, setLocalAmount] = useState("");
  const [convertedAt, setConvertedAt] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setError("");
    try {
      await createCurrencyConversion({
        budget_id: budget.id,
        donor_amount: Number(donorAmount),
        local_amount: Number(localAmount),
        converted_at: convertedAt,
      });
      queryClient.invalidateQueries({ queryKey: currencyConversionsQueryKey(budget.id) });
      queryClient.invalidateQueries({ queryKey: ledgerBalanceQueryKey(budget.id) });
      onClose();
    } catch {
      setError("Failed to record currency conversion. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Record Currency Conversion">
      <form onSubmit={handleSubmit} className="flex flex-col">
        <Input
          label={`Donor Amount (${budget.actual_currency})`}
          name="conversion_donor_amount"
          type="number"
          value={donorAmount}
          onChange={(e) => setDonorAmount(e.target.value)}
          disabled={isSaving}
          required
        />
        <Input
          label={`Local Amount (${budget.local_currency})`}
          name="conversion_local_amount"
          type="number"
          value={localAmount}
          onChange={(e) => setLocalAmount(e.target.value)}
          disabled={isSaving}
          required
        />
        <p className="text-xs text-slate-500 -mt-3 mb-4">
          Implied rate is derived, never entered directly.
        </p>
        <Input
          label="Conversion Date"
          name="conversion_converted_at"
          type="date"
          value={convertedAt}
          onChange={(e) => setConvertedAt(e.target.value)}
          disabled={isSaving}
          required
        />
        {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isSaving || !donorAmount || !localAmount || !convertedAt}
          >
            {isSaving ? "Saving..." : "Record Conversion"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
