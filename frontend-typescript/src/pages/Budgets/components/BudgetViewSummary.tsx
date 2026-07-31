import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { useDetailedBudget } from "../SingleBudgetViewContext";
import { formatCurrency } from "@/utils/currency";

export function SummaryStat({
  label,
  value,
  sub,
}: {
  label: string;
  value: string | number;
  sub?: string;
}) {
  return (
    <div>
      <div className="text-micro-label">
        {label}
      </div>
      <div className="text-stat-value mt-0.5">{value}</div>
      {sub && <div className="text-xs text-slate-500 mt-0.5">{sub}</div>}
    </div>
  );
}

export function BudgetViewSummary() {
  const { budget, totalAmount, totalReported } = useDetailedBudget();

  const categories = [...new Set(budget?.lines?.map((l) => l?.category?.name))].filter(
    Boolean,
  );
  const totalAmountNumber = Number(totalAmount);
  const reportedPct =
    totalAmountNumber > 0 ? Math.round((totalReported / totalAmountNumber) * 100) : 0;
  return (
    <Card className="w-full bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
      <CardHeader>
        <h2 className="text-section-title">
          Budget Summary
        </h2>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-8 gap-y-4">
          <SummaryStat label="Total Lines" value={budget?.lines?.length ?? 0} />
          <SummaryStat
            label="Total Amount"
            value={formatCurrency(totalAmountNumber, budget?.local_currency)}
          />
          <SummaryStat
            label="Categories"
            value={categories.length ? categories.join(", ") : "—"}
          />
          <SummaryStat
            label="Total Reported"
            value={formatCurrency(totalReported, budget?.local_currency)}
            sub={`${reportedPct}% of budget`}
          />
        </div>
      </CardContent>
    </Card>
  );
}
