import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import { TableCommon } from "@/components/ui/Table";
import { StatusBadge } from "@/pages/Budgets/components/BudgetViewHeader";
import { utcToLocal } from "@/utils/datetime";
import { formatCurrency } from "@/utils/currency";
import { getCurrentCustomerId, canRestoreBudget } from "@/utils/roleAccess";
import { createColumnHelper } from "@tanstack/react-table";
import { Edit2, Trash2, RotateCcw } from "lucide-react";

const columnHelper = createColumnHelper<any>();

const CONFIRMED_DELETE_DISABLED_TITLE =
  "Confirmed budgets can't be deleted while they may have reports, funding receipts, or currency conversions attached.";

export function TableView({
  data,
  onEdit,
  onDelete,
  onRestore,
}: {
  data: any[];
  onEdit: (budget: any) => void;
  onDelete: (budget_id: string) => void;
  onRestore: (budget_id: string) => void;
}) {
  const currentCustomerId = getCurrentCustomerId();
  const columns = [
    columnHelper.accessor("status", {
      header: "Status",
      // Same pill everywhere a budget status renders — StatusBadge, not a
      // page-local color mapping (see BudgetViewHeader's STATUS_STYLES).
      cell: (info) => <StatusBadge status={info.getValue()} />,
    }),
    columnHelper.accessor("name", { header: "Name" }),

    columnHelper.accessor("funder", {
      header: "Funder",
      cell: (info) => info.getValue()?.name || "N/A",
    }),
    columnHelper.accessor("total_amount", {
      header: "Amount",
      cell: (info) => {
        const value = info.getValue();
        return value != null
          ? formatCurrency(value, info.row.original.local_currency)
          : "N/A";
      },
    }),
    columnHelper.accessor("duration_months", {
      header: "Duration (months)",
      cell: (info) => info.getValue()?.toString() || "N/A",
    }),
    columnHelper.accessor("local_currency", {
      header: "Currency",
      cell: (info) => info.getValue() || "N/A",
    }),
    columnHelper.accessor("trace", {
      header: "Updated At",
      cell: (info) => utcToLocal(info.getValue()?.updated.event_date),
    }),
    columnHelper.accessor("trace", {
      id: "trace_updated_by",
      header: "Updated By",
      cell: (info) =>
        `${info.getValue()?.updated.user?.first_name || ""} ${
          info.getValue()?.updated.user?.last_name || ""
        }`,
    }),
    columnHelper.display({
      id: "actions",
      cell: (info) => {
        const budget = info.row.original;
        const canRestore = canRestoreBudget(budget, currentCustomerId);
        return (
          <div
            className="flex space-x-1 gap-1"
            onClick={(e) => e.stopPropagation()}
          >
            {canRestore ? (
              <Button
                onClick={() => onRestore(budget.id)}
                variant="icon"
                title="Restore budget"
              >
                <RotateCcw size={18} />
              </Button>
            ) : (
              <>
                <Button
                  onClick={() => onEdit(budget)}
                  variant="icon"
                  title="Edit budget"
                >
                  <Edit2 size={18} />
                </Button>

                <ConfirmDeleteButton
                  variant="icon-danger"
                  onConfirm={() => onDelete(budget.id)}
                  disabled={budget.status === "confirmed"}
                  title={
                    budget.status === "confirmed"
                      ? CONFIRMED_DELETE_DISABLED_TITLE
                      : "Delete budget"
                  }
                >
                  <Trash2 size={18} />
                </ConfirmDeleteButton>
              </>
            )}
          </div>
        );
      },
    }),
  ];

  const redirectToBudget = (budgetId: string) => {
    // Placeholder for redirect logic
    window.location.href = `/budgets/${budgetId}`;
  };

  return (
    <TableCommon
      data={data}
      columns={columns}
      onRowClick={(row) => redirectToBudget(row.id)}
    />
  );
}
