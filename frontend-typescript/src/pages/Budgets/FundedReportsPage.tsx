import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listFundedReports } from "@/api/reportApi";
import { fundedReportsQueryKey } from "./queryKeys";
import { formatDateOnly } from "@/utils/datetime";
import { ReportStatusBadge } from "./components/ReportStatusBadge";
import { ReportStatus, ReportWithBudgetInfo } from "./types/budget";
import Select from "@/components/ui/Select";
import { LinkButton } from "@/components/ui/LinkButton";

// The donor-side counterpart to ReportsPage.tsx: every report on a budget
// this donor funds, i.e. each grantee's reports, not this donor's own
// (there are none — a donor doesn't own budgets). Fetches the full
// cross-budget list once (GET /reports/funded/, unfiltered — small,
// nonprofit-scale data volumes per design.md) and filters client-side,
// same convention as ReportsPage.tsx/budgets.tsx.
function FundedReportsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [budgetFilter, setBudgetFilter] = useState("");
  const [granteeFilter, setGranteeFilter] = useState("");

  const {
    data: reports,
    isPending,
    isError,
  } = useQuery({
    queryKey: fundedReportsQueryKey(),
    queryFn: listFundedReports,
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

  const granteeOptions = useMemo(() => {
    const seen = new Map<string, string>();
    reportList.forEach((r) => {
      const key = r.owner_id ?? r.owner_name;
      if (key && !seen.has(key)) {
        seen.set(key, r.owner_name ?? key);
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
      const matchesGrantee =
        !granteeFilter || r.owner_id === granteeFilter || r.owner_name === granteeFilter;
      return matchesStatus && matchesBudget && matchesGrantee;
    });
  }, [reportList, statusFilter, budgetFilter, granteeFilter]);

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
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Grantee Reports</h1>
          <p className="text-gray-600">
            Every report across every budget you fund, in one place.
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
              label="Grantee"
              name="grantee-filter"
              value={granteeFilter}
              onChange={setGranteeFilter}
              options={granteeOptions}
              placeholder="All grantees"
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
                  ? "Reports across the budgets you fund will show up here."
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
                      Grantee
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
        {report.owner_name ?? "—"}
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
        {report.budget_name ?? "—"} · {report.owner_name ?? "—"}
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

export default FundedReportsPage;
