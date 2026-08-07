import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./specs",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  projects: [
    {
      name: "api",
      testDir: "./specs/api",
      use: {
        baseURL: process.env.E2E_GATEWAY_URL ?? "http://localhost:9082",
      },
    },
    {
      name: "browser",
      testDir: "./specs/browser",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: process.env.E2E_FRONTEND_URL ?? "http://localhost:4000",
      },
    },
  ],
});
