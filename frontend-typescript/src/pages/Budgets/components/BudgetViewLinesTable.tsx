import { TableCommon } from "@/components/ui/Table";
import { ColumnDef, createColumnHelper } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { BudgetLine, NewBudgetLine } from "../types/budget";
import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import { deleteBudgetLine } from "@/api/gatewayApi";
import { useMutation } from "@tanstack/react-query";
import { useDetailedBudget } from "../SingleBudgetViewContext";
import { formatCurrency } from "@/utils/currency";
import { Edit2, Trash2 } from "lucide-react";
const columnHelper = createColumnHelper<any>();

const USED_TONE_CLASSES: Record<"good" | "warn" | "danger" | "neutral", string> = {
  good: "bg-green-100 text-green-700",
  warn: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
  neutral: "bg-slate-100 text-slate-500",
};

// Compact-pill treatment for "how much of this budget line has been
// reported so far" — option B from the spend-tracking mockup
// (https://claude.ai/code/artifact/85bd0992-2081-4335-a9d2-48cfe41ec61c),
// picked over an inline progress bar and a separate spending panel.
function UsedPill({
  used,
  allocated,
  currency,
}: {
  used: number;
  allocated: number;
  currency: string | undefined;
}) {
  const pct = allocated > 0 ? Math.round((used / allocated) * 100) : null;
  const tone: "good" | "warn" | "danger" | "neutral" =
    pct === null || pct > 100 ? "danger" : pct === 100 ? "good" : pct > 0 ? "warn" : "neutral";

  return (
    <div>
      <span
        className={`inline-flex items-center text-xs font-bold px-2.5 py-0.5 rounded-full ${USED_TONE_CLASSES[tone]}`}
      >
        {pct === null ? "—" : `${pct}%`}
      </span>
      <div className="text-xs text-slate-400 mt-1">
        {formatCurrency(used, currency)} / {formatCurrency(allocated, currency)}
      </div>
    </div>
  );
}

export function BudgetViewLinesTable({
  lines,
  onEdit,
  // onDelete,
  onNew,
  onClose,
  readOnly = false,
}: {
  lines: BudgetLine[] | undefined;
  onEdit: (BudgetLine: any) => void;
  // onDelete: (budget_id: string) => void;
  onNew: () => void;
  onClose: () => void;
  readOnly?: boolean;
}) {
  const {
    budget,
    setBudget,
    budgetCategories,
    existingExtraKeys,
    budgetCategoryNames,
    spendByLineId,
  } = useDetailedBudget();
  const extraFieldKeys = useMemo((): string[] => {
    const keys = new Set<string>();
    if (!lines) return [];
    lines.forEach((line) => {
      if (line.extra_fields) {
        Object.keys(line.extra_fields).forEach((key) => keys.add(key));
      }
    });
    return Array.from(keys);
  }, [lines]);

  const mutation = useMutation({
    mutationFn: (budget_line_id: string) => {
      // Call the API to delete the budget line
      return deleteBudgetLine(budget_line_id);
    },
    onSuccess: (_, budget_line_id) => {
      // On success, you might want to refetch the budget lines or update the state
      if (!budget) return;
      console.log(
        `Budget line with id ${budget_line_id} deleted successfully.`,
      );
      const updatedBudget = {
        ...budget,
        lines: budget.lines?.filter((line) => line.id !== budget_line_id),
      };
      setBudget(updatedBudget);
    },
    onError: (error) => {
      console.error("Error deleting budget line:", error);
    },
  });

  const onDelete = (budget_line_id: string) => {
    console.log("Delete clicked for line id:", budget_line_id);
    mutation.mutate(budget_line_id);
  };
  const columns = useMemo<ColumnDef<BudgetLine>[]>(
    () => {
      const cols: ColumnDef<BudgetLine>[] = [
        {
          header: "Category",
          accessorFn: (row) => row.category?.name ?? "—",
          id: "category",
          enableSorting: true,
          enableGrouping: true,
        },
        {
          header: "Description",
          accessorKey: "description",
          enableSorting: true,
        },
        {
          header: "Amount",
          accessorKey: "amount",

          cell: (info) => (
            <span className="font-semibold text-slate-800">
              {formatCurrency(info.getValue<number>(), budget?.local_currency)}
            </span>
          ),
          aggregationFn: "sum",
          aggregatedCell: (info) => {
            const value = info.getValue() as number;
            return (
              <span className="font-semibold text-slate-800">
                Subtotal: {formatCurrency(value, budget?.local_currency)}
              </span>
            );
          },
        },
        {
          header: "Used",
          id: "used",
          accessorFn: (row: BudgetLine) => spendByLineId[row.id] ?? 0,
          aggregationFn: "sum",
          cell: (info) => (
            <UsedPill
              used={info.getValue<number>()}
              allocated={info.row.original.amount ?? 0}
              currency={budget?.local_currency}
            />
          ),
          aggregatedCell: (info) => (
            <UsedPill
              used={info.getValue() as number}
              allocated={(info.row.getValue("amount") as number) ?? 0}
              currency={budget?.local_currency}
            />
          ),
        },
        // Dynamically add columns for extra_fields
        ...extraFieldKeys.map((key: string) => ({
          header: key,
          accessorFn: (row: BudgetLine) => row.extra_fields?.[key] ?? "—",
          id: key, // important for unique identification
        })),
      ];

      if (!readOnly) {
        cols.push(
          columnHelper.display({
            id: "actions",
            enableSorting: false,
            cell: (info) => (
              <div className="flex items-center space-x-1">
                <Button
                  variant="icon"
                  onClick={() => onEdit(info.row.original)}
                  title="Edit line"
                >
                  <Edit2 size={16} />
                </Button>

                <ConfirmDeleteButton
                  variant="icon-danger"
                  title="Delete line"
                  onConfirm={() => onDelete(info.row.original.id)}
                >
                  <Trash2 size={16} />
                </ConfirmDeleteButton>
              </div>
            ),
          }),
        );
      }

      return cols;
    },
    [extraFieldKeys, readOnly, budget?.local_currency, spendByLineId],
  );

  return (
    <div className="w-full bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-section-title">
          Budget Lines
        </h2>
        {!readOnly && (
          <Button variant="secondary" onClick={onNew} className="text-sm">
            New Budget Line
          </Button>
        )}
      </div>
      <TableCommon data={lines || []} columns={columns} bare />
    </div>
  );
}
