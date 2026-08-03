import { Card, CardContent, CardHeader } from "@/components/ui/Card";
import { useDetailedBudget } from "../SingleBudgetViewContext";
import { formatCurrency } from "@/utils/currency";

// How far allocated total can drift from the donor's estimated local cap
// before it's flagged — FX rates are estimates, so small drift is expected.
const ALLOCATION_TOLERANCE_PCT = 2;

type AllocationTone = "over" | "under" | "onTarget";

function getAllocationTone(totalAmount: number, estimatedLocalCap: number): {
  tone: AllocationTone;
  diffPct: number;
} {
  if (estimatedLocalCap <= 0) return { tone: "onTarget", diffPct: 0 };
  const diffPct = ((totalAmount - estimatedLocalCap) / estimatedLocalCap) * 100;
  if (diffPct > ALLOCATION_TOLERANCE_PCT) return { tone: "over", diffPct };
  if (diffPct < -ALLOCATION_TOLERANCE_PCT) return { tone: "under", diffPct };
  return { tone: "onTarget", diffPct };
}

const ALLOCATION_STYLES: Record<
  AllocationTone,
  { text: string; pill: string; label: (diffPct: number) => string }
> = {
  over: {
    text: "text-red-600",
    pill: "bg-red-100 text-red-700",
    label: (diffPct) => `${Math.round(diffPct)}% over cap`,
  },
  under: {
    text: "text-amber-600",
    pill: "bg-amber-100 text-amber-700",
    label: (diffPct) => `${Math.round(Math.abs(diffPct))}% under cap`,
  },
  onTarget: {
    text: "text-green-600",
    pill: "bg-green-100 text-green-700",
    label: () => "on target",
  },
};

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
  const { budget, totalAmount, totalReported, hasReports } = useDetailedBudget();

  const categories = [...new Set(budget?.lines?.map((l) => l?.category?.name))].filter(
    Boolean,
  );
  const totalAmountNumber = Number(totalAmount);
  const reportedPct =
    totalAmountNumber > 0 ? Math.round((totalReported / totalAmountNumber) * 100) : 0;
  const estimatedLocalCap = budget?.estimated_local_cap;
  const hasEstimate = estimatedLocalCap != null;
  const lineCount = budget?.lines?.length ?? 0;
  const allocation = hasEstimate
    ? getAllocationTone(totalAmountNumber, estimatedLocalCap!)
    : null;
  const allocationStyle = allocation ? ALLOCATION_STYLES[allocation.tone] : null;
  return (
    <Card className="w-full bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
      <CardHeader>
        <h2 className="text-section-title">
          Budget Summary
        </h2>
      </CardHeader>
      <CardContent>
        {/* Money leads: Total Amount is the hero figure, paired against the
            donor's promise and its estimated local cap where one exists.
            Line/category counts are reference-only — see the caption below,
            not stat tiles of equal visual weight. */}
        <div className="flex flex-wrap items-baseline gap-x-5 gap-y-2">
          <div>
            <div className="text-micro-label">Total amount</div>
            <div className="flex items-baseline gap-2 mt-0.5">
              <div
                className={`text-3xl font-bold ${allocationStyle ? allocationStyle.text : "text-slate-900"}`}
              >
                {formatCurrency(totalAmountNumber, budget?.local_currency)}
              </div>
              {allocation && allocationStyle && (
                <span
                  className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold ${allocationStyle.pill}`}
                >
                  {allocationStyle.label(allocation.diffPct)}
                </span>
              )}
            </div>
          </div>
          {hasEstimate && (
            <>
              <div className="text-2xl text-slate-300 self-center" aria-hidden="true">
                ≈
              </div>
              <div className="flex flex-col">
                {/* The ≈ pairs Total Amount (real, built from lines) against
                    its OWN donor-currency equivalent — total_amount ÷
                    estimated_exchange_rate — not the flat donor_total_amount
                    promise (already shown in the header's "Donor Commitment"
                    field). Showing the promise here would misrepresent what's
                    actually been built as if it were the committed figure —
                    same "exclude/derive, don't misrepresent" rule as the
                    grantee dashboard's committed-by-currency aggregation. */}
                <span className="text-base font-bold text-slate-700">
                  {formatCurrency(
                    totalAmountNumber / budget!.estimated_exchange_rate!,
                    budget?.actual_currency,
                  )}
                </span>
                <span className="text-xs text-slate-400">
                  actual @ {budget!.estimated_exchange_rate} est. (
                  {formatCurrency(budget!.donor_total_amount!, budget?.actual_currency)} committed)
                </span>
              </div>
            </>
          )}
        </div>

        <div className="mt-3 text-xs text-slate-500">
          <span className="font-semibold text-slate-700">{lineCount}</span>{" "}
          {lineCount === 1 ? "line" : "lines"}
          {categories.length > 0 && (
            <>
              {" "}
              across <span className="font-semibold text-slate-700">{categories.join(", ")}</span>
            </>
          )}
        </div>

        {/* A budget with zero reports filed has nothing real to show here —
            an always-£0/0% stat isn't a signal worth a permanent slot. */}
        {hasReports && (
          <div className="mt-4 pt-4 border-t border-dashed border-slate-200">
            <SummaryStat
              label="Total Reported"
              value={formatCurrency(totalReported, budget?.local_currency)}
              sub={`${reportedPct}% of budget`}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
