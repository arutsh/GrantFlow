import { Page } from "@playwright/test";

export class BudgetDetailPage {
  constructor(private readonly page: Page) {}

  heading(name: string) {
    return this.page.getByRole("heading", { name, exact: true });
  }

  async addLine(description: string, amount: number) {
    await this.page.getByRole("button", { name: "New Budget Line" }).click();
    await this.page.getByLabel("Description", { exact: true }).fill(description);
    await this.page.getByLabel("Amount", { exact: true }).fill(String(amount));
    await this.page.getByRole("button", { name: "Save" }).click();
  }

  // The lines table groups rows by category and starts collapsed — the
  // single line added by this suite has no category, so there's exactly one
  // group to expand before its row (and Edit/Delete buttons) are visible.
  async expandLinesGroup() {
    await this.page.getByRole("button", { name: "Expand group" }).click();
  }

  async editLineAmount(newAmount: number) {
    await this.page.getByRole("button", { name: "Edit line" }).click();
    const amountInput = this.page.getByLabel("Amount", { exact: true });
    await amountInput.fill(String(newAmount));
    await this.page.getByRole("button", { name: "Save" }).click();
  }

  async deleteLine() {
    await this.page.getByRole("button", { name: "Delete line" }).click();
    await this.page.getByRole("button", { name: "Yes" }).click();
  }

  totalAmount() {
    return this.page
      .getByText("Total amount", { exact: true })
      .locator("xpath=following-sibling::*[1]");
  }
}
