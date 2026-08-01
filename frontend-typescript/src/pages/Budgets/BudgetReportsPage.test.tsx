import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import BudgetReportsPage from "./BudgetReportsPage";
import { Budget, Report } from "./types/budget";
import * as gatewayApi from "@/api/gatewayApi";
import * as reportApi from "@/api/reportApi";

vi.mock("@/api/gatewayApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/gatewayApi")>();
  return {
    ...actual,
    fetchBudgetById: vi.fn(),
  };
});

vi.mock("@/api/reportApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/reportApi")>();
  return {
    ...actual,
    listReportsByBudget: vi.fn(),
  };
});

const fetchBudgetByIdMock = gatewayApi.fetchBudgetById as unknown as Mock;
const listReportsByBudgetMock = reportApi.listReportsByBudget as unknown as Mock;

function makeBudget(overrides: Partial<Budget> = {}): Budget {
  return {
    id: "b1",
    name: "Clean Water Initiative — Phase 2",
    status: "confirmed",
    local_currency: "GBP",
    total_amount: 100000,
    owner: { id: "owner-1", name: "Nairobi Relief Trust" },
    ...overrides,
  };
}

function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    id: "r1",
    budget_id: "b1",
    name: "Q1 Progress Report",
    status: "approved",
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/budgets/b1/reports"]}>
        <Routes>
          <Route path="/budgets/:id/reports" element={<BudgetReportsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("BudgetReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchBudgetByIdMock.mockResolvedValue(makeBudget());
  });

  it("shows the budget's name, grantee, total allocated, and status", async () => {
    listReportsByBudgetMock.mockResolvedValue([]);
    renderPage();

    await waitFor(() =>
      expect(screen.getByText("Clean Water Initiative — Phase 2")).toBeInTheDocument(),
    );
    expect(screen.getByText("Nairobi Relief Trust")).toBeInTheDocument();
    expect(screen.getByText("£100,000")).toBeInTheDocument();
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
  });

  it("shows an empty state when the budget has no reports", async () => {
    listReportsByBudgetMock.mockResolvedValue([]);
    renderPage();

    await waitFor(() => expect(screen.getByText("No reports yet")).toBeInTheDocument());
  });

  it("lists every report's name, period, and status regardless of count", async () => {
    listReportsByBudgetMock.mockResolvedValue([
      makeReport({ id: "r1", name: "Q1 Progress Report", status: "approved" }),
      makeReport({ id: "r2", name: "Q2 Progress Report", status: "submitted" }),
      makeReport({ id: "r3", name: "Q3 Progress Report", status: "draft" }),
    ]);
    renderPage();

    // Each report renders twice (desktop table row + mobile card) — CSS
    // toggles which is visible, both exist in the DOM in jsdom.
    await waitFor(() =>
      expect(screen.getAllByText("Q1 Progress Report").length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText("Q2 Progress Report").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Q3 Progress Report").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Approved").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Submitted").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Draft").length).toBeGreaterThan(0);
  });

  it("never deep-links straight into a single report, even when there's exactly one", async () => {
    listReportsByBudgetMock.mockResolvedValue([makeReport()]);
    renderPage();

    await waitFor(() =>
      expect(screen.getAllByText("Q1 Progress Report").length).toBeGreaterThan(0),
    );
    // Still lands on the list page (its own "View Report" link), not an
    // automatic redirect into /budgets/b1/reports/r1.
    const viewLinks = screen.getAllByRole("link", { name: "View Report" });
    expect(viewLinks.length).toBeGreaterThan(0);
    for (const link of viewLinks) {
      expect(link).toHaveAttribute("href", "/budgets/b1/reports/r1");
    }
  });

  it("links each report to its detail route", async () => {
    listReportsByBudgetMock.mockResolvedValue([makeReport({ id: "r1" })]);
    renderPage();

    await waitFor(() =>
      expect(screen.getAllByText("Q1 Progress Report").length).toBeGreaterThan(0),
    );
    const viewLinks = screen.getAllByRole("link", { name: "View Report" });
    expect(viewLinks[0]).toHaveAttribute("href", "/budgets/b1/reports/r1");
  });

  it("renders both the desktop table and the mobile card list in the DOM (CSS toggles visibility)", async () => {
    listReportsByBudgetMock.mockResolvedValue([makeReport()]);
    renderPage();

    await waitFor(() => expect(screen.getAllByText("Q1 Progress Report").length).toBe(2));
  });
});
