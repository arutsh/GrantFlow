import { createAxiosInstance } from "./axiosConfig";

import {
  BudgetCategory,
  BudgetLine,
  NewBudgetLine,
} from "@/pages/Budgets/types/budget";

export const GATEWAY_BASE_URL =
  import.meta.env.VITE_API_GATEWAY || "http://localhost:8082/api/v1";

const gatewayApi = createAxiosInstance(GATEWAY_BASE_URL);

// Example API calls
export const loginUser = async (email: string, password: string) => {
  const { data } = await gatewayApi.post("/login", { email, password });
  return data;
};

export const registerUser = async (email: string, password: string) => {
  const { data } = await gatewayApi.post("/register", {
    email,
    password,
  });
  return data;
};

export const refreshToken = async (refresh_token: string) => {
  const { data } = await gatewayApi.post(
    `auth/refresh?refresh_token=${refresh_token}`,
    {}
  );
  return data;
};

export const userOnboarding = async (
  first_name: string,
  last_name: string,
  customer_name: string,
  user_id: string | null
) => {
  const { data } = await gatewayApi.patch(`/users/${user_id}/`, {
    first_name: first_name,
    last_name: last_name,
    new_customer_name: customer_name,
  });
  return data;
};

/**
 * Fetch all budgets from the API Gateway
 * based on the user's permissions.
 * If user is superuser, fetch all budgets.
 * @returns All budgets from the API Gateway
 */
export const fetchAllBudgets = async () => {
  const { data } = await gatewayApi.get(`/budgets/`);
  return data;
};

export const fetchBudgetById = async (id: string) => {
  const { data } = await gatewayApi.get(`budgets/${id}`);
  return data;
};

export const createBudgetLine = async (new_budget_line: NewBudgetLine) => {
  const { data } = await gatewayApi.post("budget-lines/", new_budget_line);
  return data;
};

export const updateBudgetLines = async (existing_budget_line: BudgetLine) => {
  console.log("updating budget line!!!", existing_budget_line);
  const { data } = await gatewayApi.patch(
    `budget-lines/${existing_budget_line.id}/`,
    existing_budget_line
  );

  return data;
};

export const deleteBudgetLine = async (budget_line_id: string) => {
  const { data } = await gatewayApi.delete(`budget-lines/${budget_line_id}/`);
  return data;
};

export const updateBudgetCategory = async (
  categoryId: string,
  updates: { name?: string; code?: string }
): Promise<BudgetCategory> => {
  const { data } = await gatewayApi.patch(
    `budget-categories/${categoryId}`,
    updates
  );
  return data;
};

export default gatewayApi;
