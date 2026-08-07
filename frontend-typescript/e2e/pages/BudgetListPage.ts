import { Page } from "@playwright/test";

export class BudgetListPage {
  constructor(private readonly page: Page) {}

  async goto() {
    await this.page.goto("/budgets");
  }

  async addBudget(name: string, funderName: string) {
    await this.page.getByRole("button", { name: "Add Budget" }).click();
    await this.page.getByPlaceholder("Budget Name").fill(name);
    await this.page.getByPlaceholder("Funder name").fill(funderName);
    await this.page.getByRole("button", { name: "Save" }).click();
  }

  row(name: string) {
    return this.page.getByRole("row", { name: new RegExp(name) });
  }

  async openBudget(name: string) {
    await this.row(name).click();
    await this.page.waitForURL(/\/budgets\/[^/]+$/);
  }

  async deleteBudget(name: string) {
    await this.row(name).getByRole("button", { name: "Delete budget" }).click();
  }
}
