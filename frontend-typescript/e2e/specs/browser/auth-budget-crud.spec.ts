import { test, expect } from "@playwright/test";
import { LoginPage } from "../../pages/LoginPage";
import { BudgetListPage } from "../../pages/BudgetListPage";
import { BudgetDetailPage } from "../../pages/BudgetDetailPage";

test("register, onboard, log in through the form, then drive the budget CRUD chain through the UI", async ({
  page,
}) => {
  const unique = crypto.randomUUID();
  const email = `e2e-browser-${unique}@example.com`;
  const password = "Passw0rd!23";
  const budgetName = `E2E Budget ${unique}`;

  // Register
  await page.goto("/register");
  await page.getByPlaceholder("Enter your email").fill(email);
  await page.getByPlaceholder("Create a password").fill(password);
  await page.getByPlaceholder("Confirm your password").fill(password);
  await page.getByRole("button", { name: "Create Account" }).click();

  // Onboard (registration auto-logs in and redirects here)
  await page.waitForURL("/onboarding");
  await page.getByLabel("First Name", { exact: false }).fill("E2E");
  await page.getByLabel("Last Name", { exact: false }).fill("Tester");
  await page
    .getByLabel("Organization / NGO", { exact: false })
    .fill(`E2E Org ${unique}`);
  await page.getByRole("button", { name: "Finish Setup" }).click();
  await page.waitForURL("/dashboard");

  // Log out, then log back in through the login form
  await page.getByRole("button", { name: new RegExp(email) }).click();
  await page.getByRole("menuitem", { name: "Logout" }).click();
  await page.waitForURL("/login");

  const loginPage = new LoginPage(page);
  await loginPage.login(email, password);
  await page.waitForURL("/dashboard");

  // Budget CRUD through the UI
  await page.getByRole("link", { name: "Budgets" }).click();
  await page.waitForURL("/budgets");

  const budgetListPage = new BudgetListPage(page);
  await budgetListPage.addBudget(budgetName, "E2E Funder");
  await expect(budgetListPage.row(budgetName)).toBeVisible();

  await budgetListPage.openBudget(budgetName);

  const budgetDetailPage = new BudgetDetailPage(page);
  await expect(budgetDetailPage.heading(budgetName)).toBeVisible();

  await budgetDetailPage.addLine("Initial line", 100);
  await expect(budgetDetailPage.totalAmount()).toContainText("100");

  await budgetDetailPage.expandLinesGroup();
  await budgetDetailPage.editLineAmount(150);
  await expect(budgetDetailPage.totalAmount()).toContainText("150");

  await budgetListPage.goto();
  await budgetListPage.deleteBudget(budgetName);
  await expect(budgetListPage.row(budgetName)).toHaveCount(0);
});
