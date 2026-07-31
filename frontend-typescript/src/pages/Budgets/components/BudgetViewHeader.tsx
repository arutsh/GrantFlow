import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { editBudget } from "@/api/budgetApi";
import { getCurrentCustomerId, isBudgetFunder, isBudgetOwner } from "@/utils/roleAccess";
import { formatDateOnly } from "@/utils/datetime";
import { Budget } from "../types/budget";

function ownerTypeLabel(owner?: { is_ngo?: boolean; is_donor?: boolean } | null): string {
  const tags = [owner?.is_ngo && "NGO", owner?.is_donor && "Donor"].filter(Boolean);
  return tags.length ? ` (${tags.join(" / ")})` : "";
}

const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  ai_draft: "AI Draft",
  confirmed: "Confirmed",
  archived: "Archived",
};

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  ai_draft: "bg-blue-100 text-blue-700",
  confirmed: "bg-green-100 text-green-700",
  archived: "bg-gray-200 text-gray-600",
};

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] ?? STATUS_STYLES.draft;
  const label = STATUS_LABELS[status] ?? status;
  return (
    <span
      className={`inline-flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide px-2.5 py-1 rounded-full mb-2 ${cls}`}
    >
      <span className="w-1.5 h-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}

export function BudgetViewHeader({
  budget,
  isLocked,
  onBudgetUpdated,
}: {
  budget: Budget;
  // Metadata/lines lock as soon as the budget is confirmed — not only once a
  // report exists (a report can only ever be created against an
  // already-confirmed budget, so "confirmed" is the correct, broader gate;
  // there's a real confirmed-but-reportless window the old report-based
  // check would have wrongly left editable).
  isLocked: boolean;
  onBudgetUpdated?: (updated: Budget) => void;
}) {
  const [isEditMode, setIsEditMode] = useState(false);
  const [name, setName] = useState(budget.name ?? "");
  const [funderName, setFunderName] = useState(
    (budget.funder as { name?: string } | null)?.name ?? ""
  );
  const [durationMonths, setDurationMonths] = useState<number | "">(
    budget.duration_months ?? ""
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  // Shared with BudgetConfirmAction/BudgetCancelConfirmationAction so the
  // Edit button can't be clicked mid-confirm/revert — without this, entering
  // edit mode while one of those requests is in flight lets a stale edit
  // form save metadata against a budget whose status just changed underneath
  // it, failing with a confusing "confirmed" edit-lock error.
  const [isActionBusy, setIsActionBusy] = useState(false);

  // AI-drafted budgets open straight into edit mode so the owner can review
  // the AI-proposed metadata/lines before they're real — same behavior as
  // the previous separate BudgetEditMode screen.
  useEffect(() => {
    if (budget.status === "ai_draft") setIsEditMode(true);
  }, [budget.status]);

  const currentCustomerId = getCurrentCustomerId();
  const owner = isBudgetOwner(budget, currentCustomerId);

  const enterEdit = () => {
    setName(budget.name ?? "");
    setFunderName((budget.funder as { name?: string } | null)?.name ?? "");
    setDurationMonths(budget.duration_months ?? "");
    setError("");
    setIsEditMode(true);
  };

  const discardEdit = () => {
    setIsEditMode(false);
    setError("");
  };

  const saveEdit = async () => {
    setIsSaving(true);
    setError("");
    try {
      const updated = await editBudget(budget.id, {
        name: name.trim() || undefined,
        // Always sent (even blank) — this form always carries the budget's
        // full current metadata, so an empty value here means the user
        // intentionally cleared it, not "leave unchanged".
        external_funder_name: funderName.trim(),
        duration_months: durationMonths !== "" ? Number(durationMonths) : undefined,
        status: budget.status === "ai_draft" ? "draft" : undefined,
      });
      onBudgetUpdated?.(updated);
      setIsEditMode(false);
    } catch {
      setError("Failed to save changes. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <Card className="w-full bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
        <CardHeader>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex-1 min-w-[240px]">
            <StatusBadge status={budget.status} />
            {isEditMode ? (
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                disabled={isSaving}
                className="block w-full max-w-md text-2xl font-semibold border border-slate-300 rounded-lg px-2 py-1 focus:outline-none focus:ring-2 focus:ring-slate-400"
              />
            ) : (
              <h1 className="text-2xl font-semibold">{budget.name}</h1>
            )}
          </div>
          <div className="flex items-center gap-2">
            {isEditMode ? (
              <>
                <Button variant="secondary" onClick={discardEdit} disabled={isSaving}>
                  Discard
                </Button>
                <Button
                  variant="primary"
                  onClick={saveEdit}
                  disabled={isSaving || !name.trim() || (durationMonths !== "" && durationMonths < 1)}
                >
                  {isSaving ? "Saving..." : "Save Changes"}
                </Button>
              </>
            ) : owner && isLocked ? (
              <span
                className="inline-flex items-center gap-1.5 text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-1.5 rounded-lg"
                title="This budget is confirmed — its metadata and lines are locked to keep reported figures accurate."
              >
                🔒 Locked: confirmed
              </span>
            ) : owner ? (
              <Button
                variant="secondary"
                onClick={enterEdit}
                className="text-sm"
                disabled={isActionBusy}
              >
                Edit
              </Button>
            ) : null}
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-slate-500 mt-1">
          Owner: <span className="text-slate-700 font-medium">{budget.owner?.name ?? "Unknown"}</span>
          {ownerTypeLabel(budget.owner)}
        </p>
        {isEditMode ? (
          <div className="mt-1 flex items-center gap-2 text-sm text-slate-500">
            <span>Funder:</span>
            <input
              type="text"
              value={funderName}
              onChange={(e) => setFunderName(e.target.value)}
              disabled={isSaving}
              className="border border-slate-300 rounded-lg px-2 py-1 text-sm text-slate-800 focus:outline-none focus:ring-2 focus:ring-slate-400"
            />
          </div>
        ) : (
          <p className="text-sm text-slate-500">
            Funder: <span className="text-slate-700 font-medium">{budget.funder?.name ?? "—"}</span>
          </p>
        )}

        {error && <p className="text-sm text-red-600 mt-2">{error}</p>}

        <div className="mt-4 flex flex-wrap gap-8 pt-4 border-t border-dashed border-slate-200">
          <div>
            <div className="text-micro-label">
              Start date
            </div>
            <div className="text-sm font-semibold text-slate-700 mt-0.5">
              {formatDateOnly(budget.start_date) ?? "—"}
            </div>
          </div>
          <div>
            <div className="text-micro-label">
              End date
            </div>
            <div className="text-sm font-semibold text-slate-700 mt-0.5">
              {formatDateOnly(budget.end_date) ?? "—"}
            </div>
          </div>
          <div>
            <div className="text-micro-label">
              Duration
            </div>
            {isEditMode ? (
              <input
                type="number"
                min={1}
                value={durationMonths}
                onChange={(e) =>
                  setDurationMonths(e.target.value ? parseInt(e.target.value) : "")
                }
                disabled={isSaving}
                className="w-20 mt-0.5 border border-slate-300 rounded-lg px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
              />
            ) : (
              <div className="text-sm font-semibold text-slate-700 mt-0.5">
                {budget.duration_months ? `${budget.duration_months} months` : "—"}
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
    {!isEditMode && (
      <>
        <BudgetConfirmAction
          budget={budget}
          onConfirmed={onBudgetUpdated}
          onBusyChange={setIsActionBusy}
        />
        <BudgetCancelConfirmationAction
          budget={budget}
          onReverted={onBudgetUpdated}
          onBusyChange={setIsActionBusy}
        />
      </>
    )}
    </>
  );
}

function BudgetConfirmAction({
  budget,
  onConfirmed,
  onBusyChange,
}: {
  budget: Budget;
  onConfirmed?: (updated: Budget) => void;
  onBusyChange?: (busy: boolean) => void;
}) {
  // Seeded from budget.start_date (not blank) so a budget that was already
  // confirmed once — then reverted via Cancel Confirmation, which leaves
  // start_date unchanged — doesn't force the owner to redundantly retype a
  // date the system already has on record.
  const [startDate, setStartDate] = useState(budget.start_date ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const currentCustomerId = getCurrentCustomerId();
  const isConfirmable = budget.status === "draft" || budget.status === "ai_draft";
  const canConfirm =
    isBudgetOwner(budget, currentCustomerId) || isBudgetFunder(budget, currentCustomerId);

  // Re-sync whenever the widget becomes visible again (e.g. after a revert),
  // covering the case where this component's state outlives the round trip
  // without a remount, not just the initial-mount case above.
  useEffect(() => {
    if (isConfirmable) setStartDate(budget.start_date ?? "");
  }, [isConfirmable, budget.start_date]);

  if (!isConfirmable || !canConfirm) return null;

  const handleConfirm = async () => {
    if (!startDate) return;
    setIsSaving(true);
    onBusyChange?.(true);
    setError("");
    try {
      const updated = await editBudget(budget.id, {
        start_date: startDate,
        status: "confirmed",
      });
      onConfirmed?.(updated);
    } catch {
      setError("Failed to confirm budget. Please try again.");
    } finally {
      setIsSaving(false);
      onBusyChange?.(false);
    }
  };

  return (
    <div className="w-full flex flex-wrap items-end gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 pt-3 pb-1">
      <span className="text-sm text-slate-600 mb-4">Confirm this budget to unlock reporting:</span>
      <Input
        label="Start Date"
        name="start_date"
        type="date"
        value={startDate}
        onChange={(e) => setStartDate(e.target.value)}
        disabled={isSaving}
      />
      <Button onClick={handleConfirm} disabled={!startDate || isSaving} className="mb-4">
        {isSaving ? "Confirming..." : "Confirm Budget"}
      </Button>
      {error && <p className="text-sm text-red-600 mb-4">{error}</p>}
    </div>
  );
}

function BudgetCancelConfirmationAction({
  budget,
  onReverted,
  onBusyChange,
}: {
  budget: Budget;
  onReverted?: (updated: Budget) => void;
  onBusyChange?: (busy: boolean) => void;
}) {
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const currentCustomerId = getCurrentCustomerId();
  if (budget.status !== "confirmed" || !isBudgetOwner(budget, currentCustomerId)) return null;

  const handleCancel = async () => {
    setIsSaving(true);
    onBusyChange?.(true);
    setError("");
    try {
      const updated = await editBudget(budget.id, { status: "draft" });
      onReverted?.(updated);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Failed to cancel confirmation. Please try again.");
    } finally {
      setIsSaving(false);
      onBusyChange?.(false);
    }
  };

  return (
    <div className="w-full flex flex-wrap items-center gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
      <span className="text-sm text-slate-500">This budget is confirmed.</span>
      <ConfirmDeleteButton
        variant="danger"
        onConfirm={handleCancel}
        disabled={isSaving}
        className="text-sm"
        confirmMessage="This will delete any draft report(s) on this budget — this can't be undone."
      >
        {isSaving ? "Cancelling..." : "Cancel Confirmation"}
      </ConfirmDeleteButton>
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}
