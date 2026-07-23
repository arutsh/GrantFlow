import {
  BudgetUpdate,
  Budget,
  CreateBudgetWithLinesRequest,
} from "@/pages/Budgets/types/budget";
import gatewayApi from "@/api/gatewayApi";

export const editBudget = async (
  id: string,
  budgetData: BudgetUpdate
): Promise<Budget> => {
  const { data } = await gatewayApi.patch(`/budgets/${id}`, budgetData);
  return data;
};

export const deleteBudget = async (id: string) => {
  const { data } = await gatewayApi.delete(`/budgets/${id}`);
  return data;
};

export const archiveBudget = async (id: string) => {
  const { data } = await gatewayApi.patch(`/budgets/${id}`, {
    status: "archived",
  });
  return data;
};

export const createBudget = async (
  budgetData: BudgetUpdate
): Promise<Budget> => {
  const { data } = await gatewayApi.post(`/budgets/`, budgetData);
  return data;
};

export const createBudgetWithLines = async (
  req: CreateBudgetWithLinesRequest
): Promise<Budget> => {
  const { data } = await gatewayApi.post("/budgets/with-lines", req);
  return data;
};
