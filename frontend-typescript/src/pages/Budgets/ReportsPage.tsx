import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listAllReports } from "@/api/reportApi";
import { allReportsQueryKey } from "./queryKeys";
import { formatDateOnly } from "@/utils/datetime";
import { ReportStatusBadge } from "./components/ReportStatusBadge";
import { ReportStatus, ReportWithBudgetInfo } from "./types/budget";
import Select from "@/components/ui/Select";
import { LinkButton } from "@/components/ui/LinkButton";

// Fixes the previously-dead "Reports" nav link (fell through to the
// catch-all redirect to /dashboard). Every report on a budget this customer
// OWNS — see FundedReportsPage.tsx for the donor-side counterpart (each
// grantee's reports against budgets this donor funds). Fetches the full
// cross-budget list once (GET /reports/, unfiltered — small, nonprofit-scale
// data volumes per design.md) and filters client-side, matching budgets.tsx's
// established convention rather than re-fetching per filter change.
function ReportsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [budgetFilter, setBudgetFilter] = useState("");
  const [donorFilter, setDonorFilter] = useState("");

  const {
    data: reports,
    isPending,
    isError,
  } = useQuery({
    queryKey: allReportsQueryKey(),
    queryFn: listAllReports,
  });

  const reportList = useMemo(() => reports ?? [], [reports]);

  const statusOptions = useMemo(() => {
    const statuses = new Set<ReportStatus>();
    reportList.forEach((r) => statuses.add(r.status));
    return Array.from(statuses).map((s) => ({ label: s, value: s }));
  }, [reportList]);

  const budgetOptions = useMemo(() => {
    const seen = new Map<string, string>();
    reportList.forEach((r) => {
      if (r.budget_id && !seen.has(r.budget_id)) {
        seen.set(r.budget_id, r.budget_name ?? r.budget_id);
      }
    });
    return Array.from(seen.entries()).map(([value, label]) => ({
      label,
      value,
    }));
  }, [reportList]);

  const donorOptions = useMemo(() => {
    const seen = new Map<string, string>();
    reportList.forEach((r) => {
      const key = r.funding_customer_id ?? r.external_funder_name;
      if (key && !seen.has(key)) {
        seen.set(key, r.external_funder_name ?? key);
      }
    });
    return Array.from(seen.entries()).map(([value, label]) => ({
      label,
      value,
    }));
  }, [reportList]);

  const filteredReports = useMemo(() => {
    return reportList.filter((r) => {
      const matchesStatus = !statusFilter || r.status === statusFilter;
      const matchesBudget = !budgetFilter || r.budget_id === budgetFilter;
      const matchesDonor =
        !donorFilter ||
        r.funding_customer_id === donorFilter ||
        r.external_funder_name === donorFilter;
      return matchesStatus && matchesBudget && matchesDonor;
    });
  }, [reportList, statusFilter, budgetFilter, donorFilter]);

  if (isPending) {
    return (
      <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
        <p className="text-sm text-slate-500 max-w-[1600px] mx-auto">
          Loading reports...
        </p>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
        <p className="text-sm text-red-600 max-w-[1600px] mx-auto">
          Failed to load reports.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
      <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-5">
        <div>
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Reports</h1>
          <p className="text-gray-600">
            Every report across every budget you own, in one place.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 sm:items-end">
          <div className="w-full sm:w-48">
            <Select
              label="Status"
              name="status-filter"
              value={statusFilter}
              onChange={setStatusFilter}
              options={statusOptions}
              placeholder="All statuses"
            />
          </div>
          <div className="w-full sm:w-64">
            <Select
              label="Budget"
              name="budget-filter"
              value={budgetFilter}
              onChange={setBudgetFilter}
              options={budgetOptions}
              placeholder="All budgets"
            />
          </div>
          <div className="w-full sm:w-64">
            <Select
              label="Donor"
              name="donor-filter"
              value={donorFilter}
              onChange={setDonorFilter}
              options={donorOptions}
              placeholder="All donors"
            />
          </div>
        </div>

        {filteredReports.length === 0 ? (
          <div className="flex items-center justify-center py-16 bg-white rounded-lg border border-slate-200">
            <div className="text-center">
              <p className="text-xl font-semibold text-slate-900 mb-2">
                No reports found
              </p>
              <p className="text-gray-600">
                {reportList.length === 0
                  ? "Reports across your budgets will show up here."
                  : "No reports match the selected filters."}
              </p>
            </div>
          </div>
        ) : (
          <>
            {/* Desktop / tablet: table */}
            <div className="hidden sm:block ledger-card overflow-x-auto">
              <table className="min-w-full divide-y divide-slate-200">
                <thead className="bg-slate-50">
                  <tr>
                    <th className="px-4 py-2.5 text-left text-micro-label">
                      Report
                    </th>
                    <th className="px-4 py-2.5 text-left text-micro-label">
                      Budget
                    </th>
                    <th className="px-4 py-2.5 text-left text-micro-label">
                      Donor
                    </th>
                    <th className="px-4 py-2.5 text-left text-micro-label">
                      Period
                    </th>
                    <th className="px-4 py-2.5 text-left text-micro-label">
                      Status
                    </th>
                    <th className="px-4 py-2.5 text-right text-micro-label">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredReports.map((report) => (
                    <ReportRow key={report.id} report={report} />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile: stacked cards instead of a table */}
            <div className="sm:hidden flex flex-col gap-3">
              {filteredReports.map((report) => (
                <ReportCard key={report.id} report={report} />
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function ReportRow({ report }: { report: ReportWithBudgetInfo }) {
  return (
    <tr className="hover:bg-slate-50">
      <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-700">
        {report.name}
      </td>
      <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-700">
        {report.budget_name ?? "—"}
      </td>
      <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-500">
        {report.external_funder_name ?? "—"}
      </td>
      <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-500">
        {formatDateOnly(report.period_start) ?? "—"} –{" "}
        {formatDateOnly(report.period_end) ?? "—"}
      </td>
      <td className="px-4 py-2.5 text-left text-sm font-normal text-slate-700">
        <ReportStatusBadge status={report.status} />
      </td>
      <td className="px-4 py-2.5 text-right text-sm font-normal text-slate-700">
        <div className="flex gap-2 justify-end">
          <LinkButton to={`/budgets/${report.budget_id}/reports/${report.id}`}>
            View Report
          </LinkButton>
          <LinkButton to={`/budgets/${report.budget_id}`}>View Budget</LinkButton>
        </div>
      </td>
    </tr>
  );
}

function ReportCard({ report }: { report: ReportWithBudgetInfo }) {
  return (
    <div className="bg-white shadow rounded p-4 flex flex-col gap-2">
      <div className="flex items-start justify-between gap-3">
        <span className="text-sm font-semibold text-slate-900">
          {report.name}
        </span>
        <ReportStatusBadge status={report.status} />
      </div>
      <span className="text-xs text-slate-500">
        {report.budget_name ?? "—"} · {report.external_funder_name ?? "—"}
      </span>
      <span className="text-xs text-slate-500">
        {formatDateOnly(report.period_start) ?? "—"} –{" "}
        {formatDateOnly(report.period_end) ?? "—"}
      </span>
      <div className="flex gap-2">
        <LinkButton
          to={`/budgets/${report.budget_id}/reports/${report.id}`}
          className="flex-1"
        >
          View Report
        </LinkButton>
        <LinkButton to={`/budgets/${report.budget_id}`} className="flex-1">
          View Budget
        </LinkButton>
      </div>
    </div>
  );
}

export default ReportsPage;
