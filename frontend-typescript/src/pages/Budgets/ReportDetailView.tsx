import { useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchBudgetById } from "@/api/gatewayApi";
import {
  createReportLine,
  getReport,
  listReportLinesByReport,
  reopenReport,
  reviewReport,
  submitReport,
} from "@/api/reportApi";
import { budgetDetailsQueryKey, reportLinesQueryKey, reportQueryKey } from "./queryKeys";
import { formatDateOnly } from "@/utils/datetime";
import { canReviewReport, getCurrentCustomerId, isBudgetOwner } from "@/utils/roleAccess";
import { ReportStatusBadge } from "./components/ReportStatusBadge";
import { ReportLineRow } from "./components/ReportLineRow";
import { SummaryStat } from "./components/BudgetViewSummary";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import Input from "@/components/ui/Input";
import Select from "@/components/ui/Select";
import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { formatCurrency } from "@/utils/currency";
import { BudgetLine, Report, ReportLine } from "./types/budget";

function ReportDetailView() {
  const { id: budgetId, reportId } = useParams<{ id: string; reportId: string }>();
  const queryClient = useQueryClient();
  const [isAddLineOpen, setIsAddLineOpen] = useState(false);

  const { data: budget } = useQuery({
    queryKey: budgetDetailsQueryKey(budgetId),
    queryFn: () => (budgetId ? fetchBudgetById(budgetId) : Promise.resolve(null)),
    enabled: !!budgetId,
  });

  const {
    data: report,
    isPending: isReportPending,
    isError: isReportError,
  } = useQuery({
    queryKey: reportQueryKey(reportId),
    queryFn: () => getReport(reportId as string),
    enabled: !!reportId,
  });

  const { data: lines } = useQuery({
    queryKey: reportLinesQueryKey(reportId),
    queryFn: () => listReportLinesByReport(reportId as string),
    enabled: !!reportId,
  });

  const currentCustomerId = getCurrentCustomerId();
  const owner = budget ? isBudgetOwner(budget, currentCustomerId) : false;
  const canReview = budget ? canReviewReport(budget, currentCustomerId) : false;

  // Union of extra_fields keys already in use across this report's lines —
  // drives both the dynamic table columns below and the prefilled/locked
  // keys offered on the "New Line" form, same convention as
  // BudgetViewLinesTable/AddBudgetLine's existingExtraKeys.
  const extraFieldKeys = useMemo(() => {
    const keys = new Set<string>();
    (lines ?? []).forEach((line) => {
      if (line.extra_fields) {
        Object.keys(line.extra_fields).forEach((key) => keys.add(key));
      }
    });
    return Array.from(keys);
  }, [lines]);

  const totalAmount = useMemo(
    () => (lines ?? []).reduce((sum, line) => sum + (line.amount ?? 0), 0),
    [lines],
  );

  const updateReportCache = (updated: Report) => {
    queryClient.setQueryData(reportQueryKey(reportId), (prev: typeof report) =>
      prev ? { ...prev, ...updated } : updated,
    );
  };

  const handleLineCreated = (line: ReportLine) => {
    setIsAddLineOpen(false);
    queryClient.setQueryData(reportLinesQueryKey(reportId), (prev: ReportLine[] | undefined) => [
      ...(prev ?? []),
      line,
    ]);
  };

  const handleLineUpdated = (updated: ReportLine) => {
    queryClient.setQueryData(reportLinesQueryKey(reportId), (prev: ReportLine[] | undefined) =>
      (prev ?? []).map((line) => (line.id === updated.id ? updated : line)),
    );
  };

  const handleLineDeleted = (lineId: string) => {
    queryClient.setQueryData(reportLinesQueryKey(reportId), (prev: ReportLine[] | undefined) =>
      (prev ?? []).filter((line) => line.id !== lineId),
    );
  };

  if (isReportPending) {
    return (
      <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
        <p className="text-sm text-slate-500 max-w-[1600px] mx-auto">Loading report...</p>
      </div>
    );
  }

  if (isReportError || !report) {
    return (
      <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
        <p className="text-sm text-red-600 max-w-[1600px] mx-auto">Failed to load this report.</p>
      </div>
    );
  }

  const isDraft = report.status === "draft";
  const canEditLines = isDraft && owner;

  return (
    <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
      <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-5">
        <Link
          to={`/budgets/${budgetId}`}
          className="text-sm text-slate-500 hover:text-slate-700 w-fit"
        >
          ← Back to budget
        </Link>

        <div className="w-full bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <h1 className="text-2xl font-semibold">{report.name}</h1>
            <ReportStatusBadge status={report.status} />
          </div>
          <p className="text-sm text-slate-500 mt-2">
            {formatDateOnly(report.period_start) ?? "—"} –{" "}
            {formatDateOnly(report.period_end) ?? "—"}
          </p>
          {report.review_notes && (
            <p className="text-sm text-slate-600 mt-2">
              Review notes: <span className="text-slate-800">{report.review_notes}</span>
            </p>
          )}
        </div>

        <Card className="w-full bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
          <CardHeader>
            <h2 className="text-section-title">Report Summary</h2>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-8 gap-y-4">
              <SummaryStat label="Total Expenses" value={lines?.length ?? 0} />
              <SummaryStat
                label="Total Amount"
                value={formatCurrency(totalAmount, budget?.local_currency)}
              />
            </div>
          </CardContent>
        </Card>

        <div className="w-full bg-white rounded-xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-section-title">Report Lines</h2>
            {canEditLines && (
              <Button variant="secondary" onClick={() => setIsAddLineOpen(true)} className="text-sm">
                New Line
              </Button>
            )}
          </div>
          {lines?.length ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold uppercase tracking-wide text-slate-500 border-b border-slate-200">
                  <th className="py-2 font-semibold">Budget Line</th>
                  <th className="py-2 font-semibold">Description</th>
                  <th className="py-2 font-semibold">Expense Date</th>
                  <th className="py-2 font-semibold text-right">Amount</th>
                  {extraFieldKeys.map((key) => (
                    <th key={key} className="py-2 font-semibold">
                      {key}
                    </th>
                  ))}
                  <th className="py-2 font-semibold text-right">Files</th>
                  {canEditLines && <th className="py-2" />}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {lines.map((line) => (
                  <ReportLineRow
                    key={line.id}
                    line={line}
                    budgetLine={budget?.lines?.find(
                      (bl: BudgetLine) => bl.id === line.budget_line_id,
                    )}
                    currency={budget?.local_currency}
                    periodStart={report.period_start}
                    periodEnd={report.period_end}
                    extraFieldKeys={extraFieldKeys}
                    editable={canEditLines}
                    onUpdated={handleLineUpdated}
                    onDeleted={handleLineDeleted}
                  />
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-sm text-slate-500">No report lines yet.</p>
          )}
        </div>

        <ReportActions
          report={report}
          owner={owner}
          canReview={canReview}
          onUpdated={updateReportCache}
        />

        {isAddLineOpen && (
          <AddReportLineModal
            reportId={report.id}
            budgetLines={budget?.lines ?? []}
            periodStart={report.period_start}
            periodEnd={report.period_end}
            existingExtraKeys={extraFieldKeys}
            isOpen={isAddLineOpen}
            onClose={() => setIsAddLineOpen(false)}
            onCreated={handleLineCreated}
          />
        )}
      </div>
    </div>
  );
}

interface ExtraField {
  key: string;
  value: string;
}

function AddReportLineModal({
  reportId,
  budgetLines,
  periodStart,
  periodEnd,
  existingExtraKeys,
  isOpen,
  onClose,
  onCreated,
}: {
  reportId: string;
  budgetLines: { id: string; description: string }[];
  periodStart?: string | null;
  periodEnd?: string | null;
  existingExtraKeys: string[];
  isOpen: boolean;
  onClose: () => void;
  onCreated: (line: ReportLine) => void;
}) {
  const [budgetLineId, setBudgetLineId] = useState("");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState<number>(0);
  const [expenseDate, setExpenseDate] = useState("");
  const [extraFields, setExtraFields] = useState<ExtraField[]>(
    existingExtraKeys.map((key) => ({ key, value: "" })),
  );
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const handleAddExtraField = () => {
    setExtraFields([...extraFields, { key: "", value: "" }]);
  };

  const handleRemoveExtraField = (index: number) => {
    setExtraFields(extraFields.filter((_, i) => i !== index));
  };

  const handleExtraFieldChange = (index: number, field: "key" | "value", value: string) => {
    const newFields = [...extraFields];
    newFields[index][field] = value;
    setExtraFields(newFields);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSaving(true);
    setError("");
    try {
      const extraFieldsObj = extraFields.reduce(
        (acc, { key, value }) => {
          if (key && value) acc[key] = value;
          return acc;
        },
        {} as Record<string, string>,
      );
      const created = await createReportLine({
        report_id: reportId,
        budget_line_id: budgetLineId,
        description: description.trim(),
        amount,
        expense_date: expenseDate,
        extra_fields: extraFieldsObj,
      });
      onCreated(created);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Failed to add report line. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="New Report Line">
      <form onSubmit={handleSubmit} className="flex flex-col">
        <Select
          label="Budget Line"
          name="budget_line_id"
          value={budgetLineId}
          onChange={setBudgetLineId}
          options={budgetLines.map((l) => ({ label: l.description, value: l.id }))}
          placeholder="-- Select Budget Line --"
          required
        />
        <Input
          label="Description"
          name="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={isSaving}
          required
        />
        <Input
          label="Amount"
          name="amount"
          type="number"
          value={amount}
          onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
          disabled={isSaving}
          required
        />
        <Input
          label="Expense Date"
          name="expense_date"
          type="date"
          value={expenseDate}
          onChange={(e) => setExpenseDate(e.target.value)}
          disabled={isSaving}
          min={periodStart ?? undefined}
          max={periodEnd ?? undefined}
          required
        />

        <div className="mb-4">
          <h3 className="font-semibold mb-2">Extra Fields</h3>
          {extraFields.map((field, index) => (
            <div key={index} className="flex gap-2 mb-2">
              <Input
                name={`extra-key-${index}`}
                showLabel={false}
                placeholder="Key"
                value={field.key}
                onChange={(e) => handleExtraFieldChange(index, "key", e.target.value)}
                disabled={isSaving || existingExtraKeys.includes(field.key)}
              />
              <Input
                name={`extra-value-${index}`}
                showLabel={false}
                placeholder="Value"
                value={field.value}
                onChange={(e) => handleExtraFieldChange(index, "value", e.target.value)}
                disabled={isSaving}
              />
              {!existingExtraKeys.includes(field.key) && (
                <Button
                  type="button"
                  onClick={() => handleRemoveExtraField(index)}
                  variant="simpleX"
                  disabled={isSaving}
                >
                  X
                </Button>
              )}
            </div>
          ))}
          <Button type="button" variant="text" onClick={handleAddExtraField} disabled={isSaving}>
            + Add Field
          </Button>
        </div>

        {error && <p className="text-sm text-red-600 mb-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={isSaving || !budgetLineId || !description.trim() || !expenseDate}
          >
            {isSaving ? "Adding..." : "Add Line"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}

function ReportActions({
  report,
  owner,
  canReview,
  onUpdated,
}: {
  report: Report;
  owner: boolean;
  canReview: boolean;
  onUpdated: (updated: Report) => void;
}) {
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const [reviewNotes, setReviewNotes] = useState("");

  const handleSubmit = async () => {
    setIsSaving(true);
    setError("");
    try {
      onUpdated(await submitReport(report.id));
    } catch {
      setError("Failed to submit report. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleReview = async (decision: "approved" | "rejected") => {
    setIsSaving(true);
    setError("");
    try {
      onUpdated(
        await reviewReport(report.id, {
          decision,
          review_notes: reviewNotes.trim() || undefined,
        }),
      );
    } catch {
      setError("Failed to submit review. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleReopen = async () => {
    setIsSaving(true);
    setError("");
    try {
      onUpdated(await reopenReport(report.id));
    } catch {
      setError("Failed to reopen report. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const showSubmit = owner && report.status === "draft";
  const showReview = canReview && report.status === "submitted";
  const showReopen = owner && report.status === "rejected";

  if (!showSubmit && !showReview && !showReopen) return null;

  return (
    <div className="w-full flex flex-col gap-3 bg-slate-50 border border-slate-200 rounded-xl px-4 py-3">
      {showSubmit && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-600">Ready to send this report for review?</span>
          <Button onClick={handleSubmit} disabled={isSaving} className="text-sm">
            {isSaving ? "Submitting..." : "Submit"}
          </Button>
        </div>
      )}
      {showReview && (
        <div className="flex flex-col gap-2">
          <label htmlFor="review_notes" className="text-sm text-slate-600">
            Review notes (optional)
          </label>
          <textarea
            id="review_notes"
            value={reviewNotes}
            onChange={(e) => setReviewNotes(e.target.value)}
            disabled={isSaving}
            rows={2}
            className="w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
          <div className="flex items-center gap-2">
            <Button
              variant="success"
              onClick={() => handleReview("approved")}
              disabled={isSaving}
              className="text-sm"
            >
              Approve
            </Button>
            <Button
              variant="danger"
              onClick={() => handleReview("rejected")}
              disabled={isSaving}
              className="text-sm"
            >
              Reject
            </Button>
          </div>
        </div>
      )}
      {showReopen && (
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-600">
            This report was rejected. Reopen it to make changes and resubmit.
          </span>
          <Button onClick={handleReopen} disabled={isSaving} className="text-sm">
            {isSaving ? "Reopening..." : "Reopen"}
          </Button>
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
    </div>
  );
}

export default ReportDetailView;
