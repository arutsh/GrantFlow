import { useState } from "react";
import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { formatCurrency } from "@/utils/currency";
import { formatDateOnly } from "@/utils/datetime";
import { updateReportLine, deleteReportLine } from "@/api/reportApi";
import { BudgetLine, ReportLine } from "../types/budget";
import { Edit2, Trash2 } from "lucide-react";

export function ReportLineRow({
  line,
  budgetLine,
  currency,
  periodStart,
  periodEnd,
  extraFieldKeys,
  // Draft-only lock, mirroring the backend's own draft-only edit/delete rule
  // for report lines (see specs/budget-report-ui/spec.md).
  editable,
  onUpdated,
  onDeleted,
}: {
  line: ReportLine;
  budgetLine: BudgetLine | undefined;
  currency: string | undefined;
  periodStart?: string | null;
  periodEnd?: string | null;
  extraFieldKeys: string[];
  editable: boolean;
  onUpdated: (line: ReportLine) => void;
  onDeleted: (lineId: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [description, setDescription] = useState(line.description ?? "");
  const [amount, setAmount] = useState<number>(line.amount ?? 0);
  const [expenseDate, setExpenseDate] = useState(line.expense_date ?? "");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const enterEdit = () => {
    setDescription(line.description ?? "");
    setAmount(line.amount ?? 0);
    setExpenseDate(line.expense_date ?? "");
    setError("");
    setIsEditing(true);
  };

  const save = async () => {
    setIsSaving(true);
    setError("");
    try {
      const updated = await updateReportLine(line.id, {
        report_id: line.report_id ?? "",
        description,
        amount,
        expense_date: expenseDate,
      });
      onUpdated(updated);
      setIsEditing(false);
    } catch (err) {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Failed to save changes. Please try again.");
    } finally {
      setIsSaving(false);
    }
  };

  const remove = async () => {
    await deleteReportLine(line.id);
    onDeleted(line.id);
  };

  return (
    <tr>
      <td className="py-2 text-sm text-slate-500 align-top">{budgetLine?.description ?? "—"}</td>
      <td className="py-2 align-top">
        {isEditing ? (
          <Input
            name={`description-${line.id}`}
            showLabel={false}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isSaving}
          />
        ) : (
          line.description ?? "—"
        )}
        {error && <p className="text-xs text-red-600 mt-1">{error}</p>}
      </td>
      <td className="py-2 align-top">
        {isEditing ? (
          <Input
            name={`expense_date-${line.id}`}
            type="date"
            showLabel={false}
            value={expenseDate}
            onChange={(e) => setExpenseDate(e.target.value)}
            disabled={isSaving}
            min={periodStart ?? undefined}
            max={periodEnd ?? undefined}
          />
        ) : (
          formatDateOnly(line.expense_date) ?? "—"
        )}
      </td>
      <td className="py-2 text-right align-top">
        {isEditing ? (
          <Input
            name={`amount-${line.id}`}
            type="number"
            showLabel={false}
            value={amount}
            onChange={(e) => setAmount(parseFloat(e.target.value) || 0)}
            disabled={isSaving}
          />
        ) : (
          <span className="font-semibold text-slate-800">
            {formatCurrency(line.amount ?? 0, currency)}
          </span>
        )}
      </td>
      {extraFieldKeys.map((key) => (
        <td key={key} className="py-2 text-sm text-slate-600 align-top">
          {String(line.extra_fields?.[key] ?? "—")}
        </td>
      ))}
      {editable && (
        <td className="py-2 text-right align-top">
          {isEditing ? (
            <div className="flex justify-end gap-1">
              <Button
                variant="secondary"
                onClick={() => setIsEditing(false)}
                disabled={isSaving}
                className="text-xs py-1 px-2"
              >
                Cancel
              </Button>
              <Button onClick={save} disabled={isSaving} className="text-xs py-1 px-2">
                {isSaving ? "Saving..." : "Save"}
              </Button>
            </div>
          ) : (
            <div className="flex justify-end items-center gap-1">
              <Button variant="icon" onClick={enterEdit} title="Edit line">
                <Edit2 size={16} />
              </Button>
              <ConfirmDeleteButton variant="icon-danger" title="Delete line" onConfirm={remove}>
                <Trash2 size={16} />
              </ConfirmDeleteButton>
            </div>
          )}
        </td>
      )}
    </tr>
  );
}
