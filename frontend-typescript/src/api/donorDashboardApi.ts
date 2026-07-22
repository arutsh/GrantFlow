import gatewayApi from "@/api/gatewayApi";

export interface CurrencyAmount {
  currency?: string;
  total_allocated: number;
}

export interface FundedBudgetsSummary {
  total_budgets: number;
  total_allocated_by_currency: CurrencyAmount[];
}

export interface GranteeSummary {
  id?: string;
  name?: string;
  country?: string;
  budgets_count: number;
  total_allocated_by_currency: CurrencyAmount[];
}

export interface FundedBudgetListItem {
  id: string;
  name: string;
  status: string;
  total_amount?: number;
  local_currency?: string;
  owner?: { id?: string; name?: string };
}

export const getFundedBudgetsSummary = async (): Promise<FundedBudgetsSummary> => {
  const { data } = await gatewayApi.get("/budgets/funded/summary");
  return data;
};

export const getFundedGrantees = async (): Promise<GranteeSummary[]> => {
  const { data } = await gatewayApi.get("/budgets/funded/grantees");
  return data;
};

export const getFundedBudgets = async (): Promise<FundedBudgetListItem[]> => {
  const { data } = await gatewayApi.get("/budgets/funded/");
  return data;
};
