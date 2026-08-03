import Button from "@/components/ui/Button";
import { SectionHead } from "@/components/ui/SectionHead";
import { formatCurrency } from "@/utils/currency";
import {
  STATUS_LABELS,
  STATUS_ORDER,
  STATUS_ACCENT,
} from "@/pages/Budgets/constants/budgetStatus";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  getGranteeDashboardSummary,
  BudgetStatusCount,
  GranteeDashboardSummary,
} from "@/api/dashboardApi";
import { granteeDashboardSummaryQueryKey } from "@/pages/Budgets/queryKeys";

const RING_RADIUS = 32;
const RING_CIRCUMFERENCE = 2 * Math.PI * RING_RADIUS;

// Fixed categorical order (see STATUS_ORDER) rather than API response order,
// so the composition bar's segment order never shuffles between loads.
function orderedStatusCounts(counts: BudgetStatusCount[]): BudgetStatusCount[] {
  return [...counts].sort(
    (a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status),
  );
}

// currencies appearing in ANY of the three per-currency figures — a
// currency with e.g. receipts but no confirmed committed budget yet should
// still get a card.
function currenciesFor(summary: GranteeDashboardSummary): string[] {
  const set = new Set<string>();
  summary.committed_by_currency.forEach(
    (c) => c.currency && set.add(c.currency),
  );
  summary.received_by_currency.forEach(
    (c) => c.currency && set.add(c.currency),
  );
  summary.conversion_progress_by_currency.forEach((c) => set.add(c.currency));
  return Array.from(set);
}

function CurrencyCard({
  summary,
  currency,
}: {
  summary: GranteeDashboardSummary;
  currency: string;
}) {
  const committed = summary.committed_by_currency.find(
    (c) => c.currency === currency,
  );
  const received = summary.received_by_currency.find(
    (c) => c.currency === currency,
  );
  const conversion = summary.conversion_progress_by_currency.find(
    (c) => c.currency === currency,
  );
  const percent = Math.max(0, Math.min(100, conversion?.percent ?? 0));
  const offset = RING_CIRCUMFERENCE * (1 - percent / 100);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col gap-4">
      <div className="w-10 h-10 rounded-full flex items-center justify-center text-[11px] font-bold font-mono bg-slate-100 text-slate-700 border border-slate-300">
        {currency}
      </div>
      <div className="flex items-center gap-4">
        <div className="relative w-20 h-20 flex-shrink-0">
          <svg
            viewBox="0 0 80 80"
            width="80"
            height="80"
            className="-rotate-90"
          >
            <circle
              cx="40"
              cy="40"
              r={RING_RADIUS}
              fill="none"
              stroke="#e2e8f0"
              strokeWidth="7"
            />
            <circle
              cx="40"
              cy="40"
              r={RING_RADIUS}
              fill="none"
              stroke="#0d9488"
              strokeWidth="7"
              strokeLinecap="round"
              strokeDasharray={RING_CIRCUMFERENCE}
              strokeDashoffset={offset}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="text-base font-bold text-slate-900 tabular-nums">
              {Math.round(percent)}%
            </span>
            <span className="text-[9px] uppercase tracking-wide text-slate-400">
              converted
            </span>
          </div>
        </div>
        <div className="flex-1 min-w-0 flex flex-col gap-2">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-xs text-slate-500 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-sm bg-amber-500" /> Confirmed
            </span>
            <span className="text-sm font-semibold tabular-nums text-slate-900">
              {formatCurrency(committed?.total_allocated ?? 0, currency)}
            </span>
          </div>
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-xs text-slate-500 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-sm bg-teal-500" /> Received
            </span>
            <span className="text-sm font-semibold tabular-nums text-slate-900">
              {formatCurrency(received?.total_allocated ?? 0, currency)}
            </span>
          </div>
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-xs text-slate-500 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-sm bg-slate-500" /> Converted
            </span>
            <span className="text-sm font-semibold tabular-nums text-slate-900">
              {formatCurrency(conversion?.converted ?? 0, currency)}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function BreakdownRow({
  row,
}: {
  row: GranteeDashboardSummary["budget_breakdown"][number];
}) {
  const burnPct =
    row.converted > 0 ? Math.round((row.spent / row.converted) * 100) : 0;
  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-2.5 text-left text-sm font-medium text-slate-900">
        {row.budget_name}
      </td>
      <td className="px-4 py-2.5 text-left text-sm text-slate-500">
        {row.external_funder_name ?? "—"}
      </td>
      <td className="px-4 py-2.5 text-right text-sm text-slate-700 tabular-nums">
        {formatCurrency(row.converted, row.local_currency ?? undefined)}
      </td>
      <td className="px-4 py-2.5 text-right text-sm text-slate-700 tabular-nums">
        {formatCurrency(row.spent, row.local_currency ?? undefined)}
      </td>
      <td className="px-4 py-2.5">
        <div className="flex items-center gap-2 min-w-[90px]">
          <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
            <span
              className={`block h-full rounded-full ${burnPct >= 100 ? "bg-green-600" : "bg-teal-500"}`}
              style={{ width: `${Math.min(100, burnPct)}%` }}
            />
          </div>
          <span className="text-xs font-mono text-slate-400 w-8 text-right">
            {burnPct}%
          </span>
        </div>
      </td>
      <td className="px-4 py-2.5 text-right text-sm text-slate-700 tabular-nums">
        {formatCurrency(row.remaining, row.local_currency ?? undefined)}
      </td>
    </tr>
  );
}

export default function GranteeDashboard() {
  const navigate = useNavigate();
  const {
    data: summary,
    isPending,
    isError,
  } = useQuery({
    queryKey: granteeDashboardSummaryQueryKey(),
    queryFn: getGranteeDashboardSummary,
  });

  if (isPending) {
    return <p className="text-sm text-slate-500">Loading dashboard...</p>;
  }
  if (isError) {
    return (
      <p className="text-sm text-red-600">Failed to load dashboard summary.</p>
    );
  }

  const orderedCounts = orderedStatusCounts(summary.budget_counts_by_status);
  const totalBudgets = orderedCounts.reduce((sum, c) => sum + c.count, 0);
  const currencies = currenciesFor(summary);

  return (
    <div className="flex flex-col">
      {/* Portfolio summary — a status composition bar (fixed categorical
          order/hues, matching StatusBadge everywhere else) rather than one
          equal-weight tile per status. */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 to-slate-700 text-white px-8 py-7 mb-10 shadow-lg">
        <div
          aria-hidden="true"
          className="absolute inset-0 opacity-[0.07] pointer-events-none"
          style={{
            backgroundImage:
              "repeating-linear-gradient(to bottom, white 0 1px, transparent 1px 30px)",
            maskImage: "linear-gradient(to bottom, black, transparent 85%)",
            WebkitMaskImage:
              "linear-gradient(to bottom, black, transparent 85%)",
          }}
        />
        <div className="relative flex flex-wrap items-end justify-between gap-10">
          <div className="min-w-[240px]">
            <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-300 mb-3">
              Budgets by status
            </p>
            <div className="text-4xl font-bold tabular-nums mb-3">
              {totalBudgets}
            </div>
            {totalBudgets > 0 && (
              <>
                <div className="flex h-2.5 rounded-full overflow-hidden gap-0.5 bg-white/10 w-full max-w-sm">
                  {orderedCounts.map((c) => (
                    <span
                      key={c.status}
                      className={STATUS_ACCENT[c.status] ?? "bg-slate-400"}
                      style={{ width: `${(c.count / totalBudgets) * 100}%` }}
                    />
                  ))}
                </div>
                <div className="flex flex-wrap gap-x-4 gap-y-1.5 mt-3 text-xs text-slate-300">
                  {orderedCounts.map((c) => (
                    <span
                      key={c.status}
                      className="inline-flex items-center gap-1.5"
                    >
                      <span
                        className={`w-2 h-2 rounded-sm ${STATUS_ACCENT[c.status] ?? "bg-slate-400"}`}
                      />
                      {STATUS_LABELS[c.status] ?? c.status} · {c.count}
                    </span>
                  ))}
                </div>
              </>
            )}
          </div>
          <div className="flex gap-8">
            <div>
              <div className="text-3xl font-bold tabular-nums">
                {summary.budget_breakdown.length}
              </div>
              <div className="text-xs text-slate-300 mt-1">
                confirmed budgets
              </div>
            </div>
            <div>
              <div className="text-3xl font-bold tabular-nums">
                {currencies.length}
              </div>
              <div className="text-xs text-slate-300 mt-1">
                {currencies.length === 1
                  ? "currency tracked"
                  : "currencies tracked"}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Committed / received / conversion progress, per donor currency —
          never blended, mirroring the mixed-currency fix already applied
          to DonorDashboard's totals. */}
      <div className="mb-12">
        <SectionHead
          title="Confirmed, Received & Converted"
          hint="figures never blended across currencies"
        />
        {currencies.length === 0 ? (
          <p className="text-gray-500">
            No confirmed budgets with a donor currency yet.
          </p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {currencies.map((currency) => (
              <CurrencyCard
                key={currency}
                summary={summary}
                currency={currency}
              />
            ))}
          </div>
        )}
      </div>

      {/* Per-budget local-currency breakdown */}
      <div className="mb-12">
        <SectionHead
          title="Budget Breakdown"
          hint={`${summary.budget_breakdown.length} confirmed`}
        />
        {summary.budget_breakdown.length === 0 ? (
          <p className="text-gray-500">No confirmed budgets yet.</p>
        ) : (
          <div className="overflow-x-auto ledger-card">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-2.5 text-left text-micro-label">
                    Budget
                  </th>
                  <th className="px-4 py-2.5 text-left text-micro-label">
                    Donor
                  </th>
                  <th className="px-4 py-2.5 text-right text-micro-label">
                    Converted
                  </th>
                  <th className="px-4 py-2.5 text-right text-micro-label">
                    Spent
                  </th>
                  <th className="px-4 py-2.5 text-left text-micro-label">
                    Burn
                  </th>
                  <th className="px-4 py-2.5 text-right text-micro-label">
                    Remaining
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {summary.budget_breakdown.map((row) => (
                  <BreakdownRow key={row.budget_id} row={row} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="mb-12">
        <SectionHead title="Quick Actions" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Button
            onClick={() => navigate("/budgets")}
            className="py-3 px-6 text-base font-medium"
            variant="primary"
          >
            View All Budgets
          </Button>
          <Button
            onClick={() => navigate("/budgets")}
            className="py-3 px-6 text-base font-medium"
            variant="outline"
          >
            Create New Budget
          </Button>
        </div>
      </div>
    </div>
  );
}
