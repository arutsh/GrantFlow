import { useNavigate } from "react-router-dom";
import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import { StatusBadge } from "@/pages/Budgets/components/BudgetViewHeader";
import { utcToLocal } from "@/utils/datetime";
import { formatCurrency } from "@/utils/currency";
import { Budget } from "../types/budget";
import { getCurrentCustomerId, canRestoreBudget } from "@/utils/roleAccess";
import {
  Edit2,
  Trash2,
  DollarSign,
  Calendar,
  User,
  RotateCcw,
} from "lucide-react";

const CONFIRMED_DELETE_DISABLED_TITLE =
  "Confirmed budgets can't be deleted while they may have reports, funding receipts, or currency conversions attached.";

export function CardsView({
  data,
  onDelete,
  onRestore,
}: {
  data: Budget[];
  onDelete: (budget_id: string) => void;
  onRestore: (budget_id: string) => void;
}) {
  const navigate = useNavigate();
  const currentCustomerId = getCurrentCustomerId();
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
      {data.map((budget: Budget) => {
        const canRestore = canRestoreBudget(budget, currentCustomerId);
        return (
          <div
            key={budget.id}
            onClick={() => navigate(`/budgets/${budget.id}`)}
            className="bg-white rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden group cursor-pointer"
          >
            {/* Card Header with Status */}
            <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
              <div className="flex items-start justify-between gap-3 mb-2">
                <h2
                  className="text-lg font-bold text-slate-900 flex-1 min-w-0 truncate"
                  title={budget.name}
                >
                  {budget.name}
                </h2>
                <StatusBadge status={budget.status} />
              </div>
              <p className="text-sm text-slate-600">
                {budget.funder?.name || "No funder"}
              </p>
            </div>

            {/* Card Body */}
            <div className="px-4 py-3 space-y-3">
              {/* Amount */}
              <div className="flex items-center gap-3 p-3 bg-slate-50 rounded-lg">
                <div className="p-2 bg-slate-100 rounded">
                  <DollarSign size={18} className="text-slate-600" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 font-medium">
                    Total Amount
                  </p>
                  <p className="text-lg font-bold text-slate-900">
                    {formatCurrency(
                      budget.total_amount ?? 0,
                      budget.local_currency,
                    )}
                  </p>
                </div>
              </div>

              {/* Duration & Currency */}
              <div className="grid grid-cols-2 gap-2">
                <div className="p-2 bg-slate-50 rounded text-center">
                  <div className="flex items-center justify-center gap-1 mb-1">
                    <Calendar size={14} className="text-slate-600" />
                  </div>
                  <p className="text-xs text-slate-500">Duration</p>
                  <p className="font-semibold text-slate-900">
                    {budget.duration_months || 0} mo
                  </p>
                </div>
                <div className="p-2 bg-slate-50 rounded text-center">
                  <p className="text-xs text-slate-500 mb-1">Currency</p>
                  <p className="font-semibold text-slate-900">
                    {budget.local_currency}
                  </p>
                </div>
              </div>

              {/* Audit Info */}
              <div className="pt-2 border-t border-slate-100 space-y-1 text-xs text-slate-500">
                <div className="flex items-center gap-1">
                  <User size={12} />
                  <span>
                    Updated by {budget?.trace?.updated?.user?.first_name}{" "}
                    {budget?.trace?.updated?.user?.last_name}
                  </span>
                </div>
                <div>{utcToLocal(budget?.trace?.updated?.event_date)}</div>
              </div>
            </div>

            {/* Card Actions */}
            <div
              className={
                canRestore
                  ? "border-t border-slate-100"
                  : "grid grid-cols-2 border-t border-slate-100"
              }
              onClick={(e) => e.stopPropagation()}
            >
              {canRestore ? (
                <Button
                  variant="ghost"
                  onClick={() => onRestore(budget.id)}
                  className="w-full flex items-center justify-center gap-1.5 min-h-[44px] rounded-none text-sm"
                >
                  <RotateCcw size={16} /> Restore
                </Button>
              ) : (
                <>
                  <Button
                    variant="ghost"
                    onClick={() => navigate(`/budgets/${budget.id}?edit=1`)}
                    className="flex items-center justify-center gap-1.5 min-h-[44px] rounded-none text-sm"
                  >
                    <Edit2 size={16} /> Edit
                  </Button>
                  <ConfirmDeleteButton
                    variant="icon-danger"
                    onConfirm={() => onDelete(budget.id)}
                    disabled={budget.status === "confirmed"}
                    title={
                      budget.status === "confirmed"
                        ? CONFIRMED_DELETE_DISABLED_TITLE
                        : undefined
                    }
                    className="flex items-center justify-center gap-1.5 min-h-[44px] rounded-none text-sm border-l border-slate-100"
                  >
                    <Trash2 size={16} /> Delete
                  </ConfirmDeleteButton>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
