import { Page } from "@playwright/test";

export class LoginPage {
  constructor(private readonly page: Page) {}

  async goto() {
    await this.page.goto("/login");
  }

  async login(email: string, password: string) {
    await this.page.getByPlaceholder("Enter your username").fill(email);
    await this.page.getByPlaceholder("Enter your password").fill(password);
    await this.page.getByRole("button", { name: "Login" }).click();
  }
}
