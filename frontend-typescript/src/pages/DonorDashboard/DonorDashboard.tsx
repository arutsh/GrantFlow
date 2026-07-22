import { useQuery } from "@tanstack/react-query";
import { createColumnHelper } from "@tanstack/react-table";
import { Link } from "react-router-dom";
import { FileText, Users, DollarSign } from "lucide-react";
import { TableCommon } from "@/components/ui/Table";
import Button from "@/components/ui/Button";
import { formatCurrency, formatCurrencyAmounts } from "@/utils/currency";
import {
  getFundedBudgetsSummary,
  getFundedGrantees,
  getFundedBudgets,
  GranteeSummary,
  FundedBudgetListItem,
} from "@/api/donorDashboardApi";

const granteeColumnHelper = createColumnHelper<GranteeSummary>();

const granteeColumns = [
  granteeColumnHelper.accessor("name", {
    header: "Grantee",
    cell: (info) => info.getValue() || "—",
  }),
  granteeColumnHelper.accessor("country", {
    header: "Country",
    cell: (info) => info.getValue() || "—",
  }),
  granteeColumnHelper.accessor("budgets_count", { header: "Budgets" }),
  granteeColumnHelper.accessor("total_allocated_by_currency", {
    header: "Total Allocated",
    cell: (info) => formatCurrencyAmounts(info.getValue()),
  }),
];

const budgetColumnHelper = createColumnHelper<FundedBudgetListItem>();

const budgetColumns = [
  budgetColumnHelper.accessor("name", { header: "Budget" }),
  budgetColumnHelper.accessor("owner", {
    header: "Grantee",
    cell: (info) => info.getValue()?.name || "—",
  }),
  budgetColumnHelper.accessor("status", {
    header: "Status",
    cell: (info) => <span className="capitalize">{info.getValue()}</span>,
  }),
  budgetColumnHelper.accessor("total_amount", {
    header: "Total Allocated",
    cell: (info) => {
      const value = info.getValue();
      return value != null
        ? formatCurrency(value, info.row.original.local_currency)
        : "—";
    },
  }),
  budgetColumnHelper.display({
    id: "actions",
    header: "Actions",
    cell: (info) => (
      <div className="flex gap-2">
        <Link
          to={`/budgets/${info.row.original.id}`}
          className="rounded-lg transition-all font-medium focus:outline-none focus:ring-2 border border-slate-300 text-slate-700 hover:bg-slate-50 focus:ring-slate-300 py-2 px-4"
        >
          View Budget
        </Link>
        <Button variant="outline" disabled title="Coming soon">
          View Reports
        </Button>
      </div>
    ),
  }),
];

export default function DonorDashboard() {
  const summaryQuery = useQuery({
    queryKey: ["donorDashboard", "summary"],
    queryFn: getFundedBudgetsSummary,
  });
  const granteesQuery = useQuery({
    queryKey: ["donorDashboard", "grantees"],
    queryFn: getFundedGrantees,
  });
  const budgetsQuery = useQuery({
    queryKey: ["donorDashboard", "budgets"],
    queryFn: getFundedBudgets,
  });

  if (
    summaryQuery.isPending ||
    granteesQuery.isPending ||
    budgetsQuery.isPending
  ) {
    return <div>Loading...</div>;
  }

  if (summaryQuery.isError || granteesQuery.isError || budgetsQuery.isError) {
    return <div>Error loading donor dashboard.</div>;
  }

  const summary = summaryQuery.data;
  const grantees = granteesQuery.data ?? [];
  const budgets = budgetsQuery.data ?? [];
  const hasFundedBudgets = budgets.length > 0;

  const stats = [
    {
      title: "Total Budgets",
      value: summary.total_budgets,
      icon: FileText,
    },
    {
      title: "Total Allocated",
      value: formatCurrencyAmounts(summary.total_allocated_by_currency),
      icon: DollarSign,
    },
    {
      title: "Total Grantees",
      value: grantees.length,
      icon: Users,
    },
  ];

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-slate-900 mb-2">
          Donor Dashboard
        </h1>
        <p className="text-gray-600">Everything you fund, in one place.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-12">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div
              key={stat.title}
              className="bg-slate-100 rounded-lg card-shadow-hover p-6 transition-all"
            >
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-gray-600 text-sm font-medium mb-1">
                    {stat.title}
                  </p>
                  <p className="text-3xl font-bold text-slate-900">
                    {stat.value}
                  </p>
                </div>
                <div className="p-2 rounded-lg bg-slate-100">
                  <Icon size={24} className="text-slate-700" />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {!hasFundedBudgets ? (
        <div className="flex items-center justify-center py-16 bg-white rounded-lg border border-slate-200">
          <div className="text-center">
            <p className="text-xl font-semibold text-slate-900 mb-2">
              No funded budgets yet
            </p>
            <p className="text-gray-600">
              Budgets you fund will show up here once they're created.
            </p>
          </div>
        </div>
      ) : (
        <>
          <div className="mb-12">
            <h2 className="text-2xl font-bold text-slate-900 mb-4">
              Grantees
            </h2>
            <TableCommon data={grantees} columns={granteeColumns} />
          </div>

          <div>
            <h2 className="text-2xl font-bold text-slate-900 mb-4">
              Funded Budgets
            </h2>
            <TableCommon data={budgets} columns={budgetColumns} />
          </div>
        </>
      )}
    </div>
  );
}
