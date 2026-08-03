import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import ReportsPage from "./ReportsPage";
import { ReportWithBudgetInfo } from "./types/budget";
import * as reportApi from "@/api/reportApi";

vi.mock("@/api/reportApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/reportApi")>();
  return {
    ...actual,
    listAllReports: vi.fn(),
  };
});

const listAllReportsMock = reportApi.listAllReports as unknown as Mock;

function makeReport(overrides: Partial<ReportWithBudgetInfo> = {}): ReportWithBudgetInfo {
  return {
    id: "r1",
    budget_id: "b1",
    name: "Q1 Progress Report",
    status: "approved",
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    budget_name: "Clean Water Initiative",
    budget_status: "confirmed",
    funding_customer_id: "d1",
    external_funder_name: "Acme Foundation",
    ...overrides,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/reports"]}>
        <Routes>
          <Route path="/reports" element={<ReportsPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ReportsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows the report name, budget, donor, period, and status for each row", async () => {
    listAllReportsMock.mockResolvedValue([makeReport()]);
    renderPage();

    await waitFor(() =>
      expect(screen.getAllByText("Q1 Progress Report").length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText("Clean Water Initiative").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Acme Foundation").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Approved").length).toBeGreaterThan(0);
  });

  it("View Budget navigates to the report's parent budget", async () => {
    listAllReportsMock.mockResolvedValue([makeReport({ id: "r1", budget_id: "b1" })]);
    renderPage();

    await waitFor(() =>
      expect(screen.getAllByRole("link", { name: "View Budget" }).length).toBeGreaterThan(0),
    );
    const links = screen.getAllByRole("link", { name: "View Budget" });
    for (const link of links) {
      expect(link).toHaveAttribute("href", "/budgets/b1");
    }
  });

  it("filtering by status narrows the visible rows", async () => {
    listAllReportsMock.mockResolvedValue([
      makeReport({ id: "r1", name: "Approved Report", status: "approved" }),
      makeReport({ id: "r2", name: "Draft Report", status: "draft" }),
    ]);
    renderPage();

    await waitFor(() =>
      expect(screen.getAllByText("Approved Report").length).toBeGreaterThan(0),
    );
    expect(screen.getAllByText("Draft Report").length).toBeGreaterThan(0);

    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "approved" } });

    await waitFor(() =>
      expect(screen.queryAllByText("Draft Report").length).toBe(0),
    );
    expect(screen.getAllByText("Approved Report").length).toBeGreaterThan(0);
  });

  it("filtering by budget narrows the visible rows", async () => {
    listAllReportsMock.mockResolvedValue([
      makeReport({ id: "r1", name: "Report A", budget_id: "b1", budget_name: "Budget A" }),
      makeReport({ id: "r2", name: "Report B", budget_id: "b2", budget_name: "Budget B" }),
    ]);
    renderPage();

    await waitFor(() => expect(screen.getAllByText("Report A").length).toBeGreaterThan(0));

    fireEvent.change(screen.getByLabelText("Budget"), { target: { value: "b1" } });

    await waitFor(() => expect(screen.queryAllByText("Report B").length).toBe(0));
    expect(screen.getAllByText("Report A").length).toBeGreaterThan(0);
  });

  it("filtering by donor narrows the visible rows", async () => {
    listAllReportsMock.mockResolvedValue([
      makeReport({
        id: "r1",
        name: "Report A",
        funding_customer_id: "d1",
        external_funder_name: "Donor One",
      }),
      makeReport({
        id: "r2",
        name: "Report B",
        funding_customer_id: "d2",
        external_funder_name: "Donor Two",
      }),
    ]);
    renderPage();

    await waitFor(() => expect(screen.getAllByText("Report A").length).toBeGreaterThan(0));

    fireEvent.change(screen.getByLabelText("Donor"), { target: { value: "d1" } });

    await waitFor(() => expect(screen.queryAllByText("Report B").length).toBe(0));
    expect(screen.getAllByText("Report A").length).toBeGreaterThan(0);
  });

  it("shows an empty state when there are no reports", async () => {
    listAllReportsMock.mockResolvedValue([]);
    renderPage();

    await waitFor(() => expect(screen.getByText("No reports found")).toBeInTheDocument());
    expect(
      screen.getByText("Reports across your budgets will show up here."),
    ).toBeInTheDocument();
  });

  it("shows a filtered empty state when filters exclude every report", async () => {
    listAllReportsMock.mockResolvedValue([
      makeReport({ id: "r1", status: "approved", budget_id: "b1", budget_name: "Budget A" }),
      makeReport({
        id: "r2",
        name: "Other Report",
        status: "draft",
        budget_id: "b2",
        budget_name: "Budget B",
      }),
    ]);
    renderPage();

    await waitFor(() =>
      expect(screen.getAllByText("Q1 Progress Report").length).toBeGreaterThan(0),
    );

    // No single report is both approved AND on Budget B — a combination
    // that excludes every row, even though each filter option individually
    // matches something.
    fireEvent.change(screen.getByLabelText("Status"), { target: { value: "approved" } });
    fireEvent.change(screen.getByLabelText("Budget"), { target: { value: "b2" } });

    await waitFor(() => expect(screen.getByText("No reports found")).toBeInTheDocument());
    expect(screen.getByText("No reports match the selected filters.")).toBeInTheDocument();
  });

  it("renders both the desktop table and the mobile card list in the DOM (CSS toggles visibility)", async () => {
    listAllReportsMock.mockResolvedValue([makeReport()]);
    renderPage();

    await waitFor(() => expect(screen.getAllByText("Q1 Progress Report").length).toBe(2));
  });
});
