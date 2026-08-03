import gatewayApi from "@/api/gatewayApi";
import { CurrencyAmount } from "@/api/donorDashboardApi";

export interface BudgetStatusCount {
  status: string;
  count: number;
}

export interface ConversionProgress {
  currency: string;
  received: number;
  converted: number;
  // 0-100
  percent: number;
}

export interface BudgetBreakdownRow {
  budget_id: string;
  budget_name: string;
  funding_customer_id?: string | null;
  external_funder_name?: string | null;
  local_currency?: string | null;
  converted: number;
  spent: number;
  remaining: number;
}

export interface GranteeDashboardSummary {
  budget_counts_by_status: BudgetStatusCount[];
  committed_by_currency: CurrencyAmount[];
  received_by_currency: CurrencyAmount[];
  conversion_progress_by_currency: ConversionProgress[];
  budget_breakdown: BudgetBreakdownRow[];
}

export const getGranteeDashboardSummary = async (): Promise<GranteeDashboardSummary> => {
  const { data } = await gatewayApi.get("/budgets/dashboard/summary");
  return data;
};
