import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { fetchBudgetById } from "@/api/gatewayApi";
import { listReportsByBudget } from "@/api/reportApi";
import { budgetDetailsQueryKey, reportsByBudgetQueryKey } from "./queryKeys";
import { formatDateOnly } from "@/utils/datetime";
import { formatCurrency } from "@/utils/currency";
import { StatusBadge } from "./components/BudgetViewHeader";
import { ReportStatusBadge } from "./components/ReportStatusBadge";
import { LinkButton } from "@/components/ui/LinkButton";

// A dedicated, always-a-list reports page for one budget — the funder's
// entry point from DonorDashboard's "View Reports". Never deep-links
// straight into a single report, even when there's only one (see
// design.md's resolved open question). Reuses the same data layer as the
// grantee-side inline ReportsList (ticket #159/#161) — no new API calls —
// but is its own presentational shell: a header matching BudgetViewHeader's
// card treatment, and a table matching DonorDashboard's own "Funded
// Budgets" table look. Below the `sm` breakpoint, the table (hidden via
// `hidden sm:block`) gives way to a stacked-card list (`sm:hidden`) instead
// — Table.tsx/TableCommon has no built-in card-fallback today, so this page
// hand-rolls its own breakpoint swap in pure CSS, per the signed-off
// mockup from 2026-07-31.
function BudgetReportsPage() {
  const { id: budgetId } = useParams<{ id: string }>();

  const { data: budget } = useQuery({
    queryKey: budgetDetailsQueryKey(budgetId),
    queryFn: () => (budgetId ? fetchBudgetById(budgetId) : Promise.resolve(null)),
    enabled: !!budgetId,
  });

  const {
    data: reports,
    isPending,
    isError,
  } = useQuery({
    queryKey: reportsByBudgetQueryKey(budgetId),
    queryFn: () => listReportsByBudget(budgetId as string),
    enabled: !!budgetId,
  });

  if (isPending || !budget) {
    return (
      <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
        <p className="text-sm text-slate-500 max-w-[1600px] mx-auto">Loading reports...</p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
        <p className="text-sm text-red-600 max-w-[1600px] mx-auto">
          Failed to load reports for this budget.
        </p>
      </div>
    );
  }

  const reportList = reports ?? [];

  return (
    <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
      <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-5">
        <Link
          to={`/budgets/${budgetId}`}
          className="text-sm text-slate-500 hover:text-slate-700 w-fit"
        >
          ← Back to budget
        </Link>

        <div className="w-full bg-white rounded-xl border border-slate-200 shadow-sm px-6 py-5">
          <StatusBadge status={budget.status} />
          <h1 className="text-2xl font-semibold">{budget.name}</h1>
          <p className="text-sm text-slate-500 mt-1">
            Grantee: <span className="text-slate-700 font-medium">{budget.owner?.name ?? "Unknown"}</span>
            {" · "}
            Total allocated:{" "}
            <span className="text-slate-700 font-medium">
              {formatCurrency(budget.total_amount ?? 0, budget.local_currency)}
            </span>
          </p>
        </div>

        <div>
          <h2 className="text-2xl font-bold text-slate-900 mb-4">Reports</h2>

          {reportList.length === 0 ? (
            <div className="flex items-center justify-center py-16 bg-white rounded-lg border border-slate-200">
              <div className="text-center">
                <p className="text-xl font-semibold text-slate-900 mb-2">No reports yet</p>
                <p className="text-gray-600">
                  Reports the grantee submits for this budget will show up here.
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Desktop / tablet: table, matching TableCommon's own default look */}
              <div className="hidden sm:block ledger-card overflow-x-auto">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-2.5 text-left text-micro-label">Report</th>
                      <th className="px-4 py-2.5 text-left text-micro-label">Period</th>
                      <th className="px-4 py-2.5 text-left text-micro-label">Status</th>
                      <th className="px-4 py-2.5 text-right text-micro-label">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {reportList.map((report) => (
                      <tr key={report.id} className="hover:bg-slate-50">
                        <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-700">
                          {report.name}
                        </td>
                        <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-500">
                          {formatDateOnly(report.period_start) ?? "—"} –{" "}
                          {formatDateOnly(report.period_end) ?? "—"}
                        </td>
                        <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-700">
                          <ReportStatusBadge status={report.status} />
                        </td>
                        <td className="px-4 py-2.5 text-right text-sm font-normal text-slate-700">
                          <LinkButton to={`/budgets/${budgetId}/reports/${report.id}`}>
                            View Report
                          </LinkButton>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile: stacked cards instead of a table */}
              <div className="sm:hidden flex flex-col gap-3">
                {reportList.map((report) => (
                  <div
                    key={report.id}
                    className="bg-white shadow rounded p-4 flex flex-col gap-2"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <span className="text-sm font-semibold text-slate-900">{report.name}</span>
                      <ReportStatusBadge status={report.status} />
                    </div>
                    <span className="text-xs text-slate-500">
                      {formatDateOnly(report.period_start) ?? "—"} –{" "}
                      {formatDateOnly(report.period_end) ?? "—"}
                    </span>
                    <LinkButton to={`/budgets/${budgetId}/reports/${report.id}`}>
                      View Report
                    </LinkButton>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default BudgetReportsPage;
