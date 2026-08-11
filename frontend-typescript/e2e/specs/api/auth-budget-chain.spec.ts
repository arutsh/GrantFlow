import { test, expect, request as pwRequest } from "@playwright/test";
import { jwtDecode } from "jwt-decode";

interface TokenResponse {
  access_token: string;
  token_type: string;
  refresh_token: string;
  status: string;
}

interface JwtPayload {
  user_id: string;
}

// Register issues a token for a "pending" user with no org attached yet;
// budgets require an owner_id (customer_id), so the chain onboards the user
// (creating an org) before logging back in to pick up a token whose claims
// actually carry that customer_id — mirrors the real Register -> Onboarding
// -> Dashboard flow in the frontend (see src/pages/OnBoarding.tsx).
test("register, onboard, login, then drive the budget CRUD chain", async ({
  request,
  baseURL,
}) => {
  const unique = crypto.randomUUID();
  const email = `e2e-${unique}@example.com`;
  const password = "Passw0rd!23";

  const registerRes = await request.post("/api/v1/register", {
    data: {
      email,
      password,
      first_name: "E2E",
      last_name: "Tester",
      consent_data_processing: true,
    },
  });
  expect(registerRes.status()).toBe(200);
  const registerBody: TokenResponse = await registerRes.json();
  expect(registerBody.access_token).toBeTruthy();

  const userId = jwtDecode<JwtPayload>(registerBody.access_token).user_id;
  expect(userId).toBeTruthy();

  const registerContext = await pwRequest.newContext({
    baseURL,
    extraHTTPHeaders: { Authorization: `Bearer ${registerBody.access_token}` },
  });
  const onboardRes = await registerContext.patch(`/api/v1/users/${userId}/`, {
    data: { new_customer_name: `E2E Org ${unique}` },
  });
  expect(onboardRes.status()).toBe(200);
  await registerContext.dispose();

  const loginRes = await request.post("/api/v1/auth/login", {
    data: { email, password },
  });
  expect(loginRes.status()).toBe(200);
  const loginBody: TokenResponse = await loginRes.json();
  expect(loginBody.access_token).toBeTruthy();

  const authed = await pwRequest.newContext({
    baseURL,
    extraHTTPHeaders: { Authorization: `Bearer ${loginBody.access_token}` },
  });

  try {
    const createBudgetRes = await authed.post("/api/v1/budgets/", {
      data: {
        name: `E2E Budget ${unique}`,
        external_funder_name: "E2E Funder",
        local_currency: "USD",
        actual_currency: "USD",
      },
    });
    expect(createBudgetRes.status()).toBe(200);
    const budget = await createBudgetRes.json();
    expect(budget.id).toBeTruthy();
    const budgetId: string = budget.id;

    const addLineRes = await authed.post("/api/v1/budget-lines/", {
      data: { budget_id: budgetId, description: "Initial line", amount: 100 },
    });
    expect(addLineRes.status()).toBe(200);
    const line = await addLineRes.json();
    expect(line.id).toBeTruthy();
    const lineId: string = line.id;

    const updateLineRes = await authed.patch(`/api/v1/budget-lines/${lineId}/`, {
      data: { budget_id: budgetId, amount: 150 },
    });
    expect(updateLineRes.status()).toBe(200);
    const updatedLine = await updateLineRes.json();
    expect(updatedLine.amount).toBe(150);

    const getBudgetRes = await authed.get(`/api/v1/budgets/${budgetId}`);
    expect(getBudgetRes.status()).toBe(200);
    const budgetWithLines = await getBudgetRes.json();
    expect(budgetWithLines.total_amount).toBe(150);
    expect(budgetWithLines.lines).toHaveLength(1);

    const deleteLineRes = await authed.delete(`/api/v1/budget-lines/${lineId}/`);
    expect(deleteLineRes.status()).toBe(200);

    const getAfterDeleteRes = await authed.get(`/api/v1/budgets/${budgetId}`);
    expect(getAfterDeleteRes.status()).toBe(200);
    const budgetAfterDelete = await getAfterDeleteRes.json();
    expect(budgetAfterDelete.total_amount).toBe(0);
    expect(budgetAfterDelete.lines).toHaveLength(0);

    const deleteBudgetRes = await authed.delete(`/api/v1/budgets/${budgetId}`);
    expect(deleteBudgetRes.status()).toBe(200);
    const deleteBudgetBody = await deleteBudgetRes.json();
    expect(deleteBudgetBody.success).toBe(true);
  } finally {
    await authed.dispose();
  }
});
