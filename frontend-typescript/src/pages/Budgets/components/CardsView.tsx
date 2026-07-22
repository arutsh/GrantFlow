import Button from "@/components/ui/Button";
import { utcToLocal } from "@/utils/datetime";
import { formatCurrency } from "@/utils/currency";
import { Budget } from "../types/budget";
import { Edit2, Trash2, DollarSign, Calendar, User } from "lucide-react";

export function CardsView({
  data,
  onEdit,
  onDelete,
}: {
  data: Budget[];
  onEdit: (budget: Budget) => void;
  onDelete: (budget_id: string) => void;
}) {
  const getStatusColor = (status: string) => {
    switch (status?.toLowerCase()) {
      case "approved":
        return "bg-green-100 text-green-800";
      case "draft":
        return "bg-yellow-100 text-yellow-800";
      case "rejected":
        return "bg-red-100 text-red-800";
      default:
        return "bg-slate-100 text-slate-800";
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 w-full">
      {data.map((budget: Budget) => (
        <div
          key={budget.id}
          className="bg-white rounded-lg border border-slate-200 shadow-sm hover:shadow-md transition-all duration-200 overflow-hidden group"
        >
          {/* Card Header with Status */}
          <div className="px-4 py-3 border-b border-slate-100 bg-gradient-to-r from-slate-50 to-white">
            <div className="flex items-start justify-between gap-3 mb-2">
              <h2 className="text-lg font-bold text-slate-900 flex-1">
                {budget.name}
              </h2>
              <span
                className={`px-3 py-1 rounded-full text-xs font-semibold ${getStatusColor(budget.status)}`}
              >
                {budget.status}
              </span>
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
                  {formatCurrency(budget.total_amount ?? 0, budget.local_currency)}
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
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-100 flex gap-2 justify-end">
            <Button
              variant="secondary"
              onClick={() => onEdit(budget)}
              className="flex items-center justify-center gap-1 py-1 px-3 text-sm"
            >
              <Edit2 size={14} /> Edit
            </Button>
            <Button
              variant="danger"
              onClick={() => onDelete(budget.id)}
              className="flex items-center justify-center gap-1 py-1 px-3 text-sm"
            >
              <Trash2 size={14} /> Delete
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
