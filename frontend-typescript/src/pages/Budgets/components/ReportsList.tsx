import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Input from "@/components/ui/Input";
import { createReport, listReportsByBudget } from "@/api/reportApi";
import { reportsByBudgetQueryKey } from "../queryKeys";
import { getCurrentCustomerId, isBudgetOwner } from "@/utils/roleAccess";
import { formatDateOnly } from "@/utils/datetime";
import { Budget } from "../types/budget";
import { ReportStatusBadge } from "./ReportStatusBadge";

export function ReportsList({ budget }: { budget: Budget }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const currentCustomerId = getCurrentCustomerId();
  const owner = isBudgetOwner(budget, currentCustomerId);

  const { data: reports } = useQuery({
    queryKey: reportsByBudgetQueryKey(budget.id),
    queryFn: () => listReportsByBudget(budget.id),
    enabled: !!budget.id,
  });

  // A confirmed budget always shows the section (even with zero reports yet,
  // via the empty state); a non-confirmed budget (e.g. later archived) still
  // shows it if historical reports exist.
  const shouldShow = budget.status === "confirmed" || !!reports?.length;
  if (!shouldShow) return null;

  const handleCreated = (reportId: string) => {
    setIsCreateOpen(false);
    queryClient.invalidateQueries({ queryKey: reportsByBudgetQueryKey(budget.id) });
    navigate(`/budgets/${budget.id}/reports/${reportId}`);
  };

  return (
    <div className="w-full bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-section-title">Reports</h2>
        {owner && (
          <Button variant="secondary" onClick={() => setIsCreateOpen(true)} className="text-sm">
            New Report
          </Button>
        )}
      </div>

      {reports?.length ? (
        <ul className="divide-y divide-slate-100">
          {reports.map((report) => (
            <li key={report.id}>
              <button
                type="button"
                onClick={() => navigate(`/budgets/${budget.id}/reports/${report.id}`)}
                className="w-full flex items-center justify-between gap-4 py-3 text-left hover:bg-slate-50 rounded-lg px-2 -mx-2"
              >
                <div>
                  <div className="text-sm font-medium text-slate-800">{report.name}</div>
                  <div className="text-xs text-slate-500 mt-0.5">
                    {formatDateOnly(report.period_start) ?? "—"} –{" "}
                    {formatDateOnly(report.period_end) ?? "—"}
                  </div>
                </div>
                <ReportStatusBadge status={report.status} />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-sm text-slate-500">No reports yet.</p>
      )}

      {isCreateOpen && (
        <NewReportModal
          budgetId={budget.id}
          isOpen={isCreateOpen}
          onClose={() => setIsCreateOpen(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  );
}

function NewReportModal({
  budgetId,
  isOpen,
  onClose,
  onCreated,
}: {
  budgetId: string;
  isOpen: boolean;
  onClose: () => void;
  onCreated: (reportId: string) => void;
}) {
  const [name, setName] = useState("");
  const [periodStart, setPeriodStart] = useState("");
  const [periodEnd, setPeriodEnd] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setError("");
    try {
      const created = await createReport({
        budget_id: budgetId,
        name: name.trim(),
        period_start: periodStart || undefined,
        period_end: periodEnd || undefined,
      });
      onCreated(created.id);
    } catch (err) {
      // Backend validation errors (e.g. overlapping period) are surfaced
      // inline and the form's entered values are left intact — the modal
      // only closes on success.
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Failed to create report. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="New Report">
      <form onSubmit={handleSubmit} className="flex flex-col">
        <Input
          label="Name"
          name="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isSaving}
          required
        />
        <Input
          label="Period Start (optional)"
          name="period_start"
          type="date"
          value={periodStart}
          onChange={(e) => setPeriodStart(e.target.value)}
          disabled={isSaving}
        />
        <Input
          label="Period End (optional)"
          name="period_end"
          type="date"
          value={periodEnd}
          onChange={(e) => setPeriodEnd(e.target.value)}
          disabled={isSaving}
        />
        {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSaving || !name.trim()}>
            {isSaving ? "Creating..." : "Create Report"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
