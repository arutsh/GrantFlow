import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { useDetailedBudget } from "../SingleBudgetViewContext";
import { formatCurrency } from "@/utils/currency";

function SummaryStat({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <div className="text-micro-label">
        {label}
      </div>
      <div className="text-stat-value mt-0.5">{value}</div>
    </div>
  );
}

export function BudgetViewSummary() {
  const { budget, totalAmount } = useDetailedBudget();

  const categories = [...new Set(budget?.lines?.map((l) => l?.category?.name))].filter(
    Boolean,
  );
  return (
    <Card className="w-full bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
      <CardHeader>
        <h2 className="text-section-title">
          Budget Summary
        </h2>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-8 gap-y-4">
          <SummaryStat label="Total Lines" value={budget?.lines?.length ?? 0} />
          <SummaryStat
            label="Total Amount"
            value={formatCurrency(Number(totalAmount), budget?.local_currency)}
          />
          <SummaryStat
            label="Categories"
            value={categories.length ? categories.join(", ") : "—"}
          />
        </div>
      </CardContent>
    </Card>
  );
}
