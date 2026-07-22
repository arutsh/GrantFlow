import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import DonorDashboard from "./DonorDashboard";
import * as donorDashboardApi from "@/api/donorDashboardApi";

vi.mock("@/api/donorDashboardApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/donorDashboardApi")>();
  return {
    ...actual,
    getFundedBudgetsSummary: vi.fn(),
    getFundedGrantees: vi.fn(),
    getFundedBudgets: vi.fn(),
  };
});

const getFundedBudgetsSummaryMock = donorDashboardApi.getFundedBudgetsSummary as unknown as ReturnType<
  typeof vi.fn
>;
const getFundedGranteesMock = donorDashboardApi.getFundedGrantees as unknown as ReturnType<
  typeof vi.fn
>;
const getFundedBudgetsMock = donorDashboardApi.getFundedBudgets as unknown as ReturnType<
  typeof vi.fn
>;

function renderDashboard() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DonorDashboard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("DonorDashboard", () => {
  it("renders stat tiles, grantee table, and funded-budgets table with real-shaped data", async () => {
    getFundedBudgetsSummaryMock.mockResolvedValue({
      total_budgets: 3,
      total_allocated_by_currency: [{ currency: "GBP", total_allocated: 2200 }],
    });
    getFundedGranteesMock.mockResolvedValue([
      {
        id: "g1",
        name: "Hope Relief NGO",
        country: "GB",
        budgets_count: 2,
        total_allocated_by_currency: [{ currency: "GBP", total_allocated: 1500 }],
      },
      {
        id: "g2",
        name: "Clean Water Trust",
        country: "GB",
        budgets_count: 1,
        total_allocated_by_currency: [{ currency: "GBP", total_allocated: 700 }],
      },
    ]);
    getFundedBudgetsMock.mockResolvedValue([
      {
        id: "b1",
        name: "Clean Water Phase 1",
        status: "draft",
        total_amount: 1000,
        local_currency: "GBP",
        owner: { id: "g1", name: "Hope Relief NGO" },
      },
      {
        id: "b2",
        name: "School Rebuild",
        status: "confirmed",
        total_amount: 700,
        local_currency: "GBP",
        owner: { id: "g2", name: "Clean Water Trust" },
      },
    ]);

    renderDashboard();

    await waitFor(() => expect(screen.getByText("3")).toBeInTheDocument());

    // Stat tiles
    expect(screen.getByText("Total Budgets")).toBeInTheDocument();
    expect(screen.getByText("£2,200")).toBeInTheDocument();
    expect(screen.getByText("Total Grantees")).toBeInTheDocument();

    // Grantee table rows — proves TableCommon (with its hardcoded
    // grouping=["category"] initialState) renders fine against data that has
    // no "category" column at all. Both grantee names also appear as the
    // funded-budgets table's "owner" column, hence getAllByText.
    expect(screen.getAllByText("Hope Relief NGO").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Clean Water Trust").length).toBeGreaterThan(0);
    expect(screen.getByText("£1,500")).toBeInTheDocument();

    // Funded-budgets table rows
    expect(screen.getByText("Clean Water Phase 1")).toBeInTheDocument();
    expect(screen.getByText("School Rebuild")).toBeInTheDocument();

    // Disabled "View Reports" with "Coming soon" tooltip, no fabricated data
    const reportButtons = screen.getAllByRole("button", { name: "View Reports" });
    expect(reportButtons).toHaveLength(2);
    for (const button of reportButtons) {
      expect(button).toBeDisabled();
      expect(button).toHaveAttribute("title", "Coming soon");
    }

    // "View Budget" links to the real budget detail page
    const viewBudgetLinks = screen.getAllByRole("link", { name: "View Budget" });
    expect(viewBudgetLinks).toHaveLength(2);
    expect(viewBudgetLinks[0]).toHaveAttribute("href", "/budgets/b1");
    expect(viewBudgetLinks[1]).toHaveAttribute("href", "/budgets/b2");
  });

  it("renders each currency's total separately instead of blending them", async () => {
    getFundedBudgetsSummaryMock.mockResolvedValue({
      total_budgets: 2,
      total_allocated_by_currency: [
        { currency: "GBP", total_allocated: 3000 },
        { currency: "USD", total_allocated: 5000 },
      ],
    });
    getFundedGranteesMock.mockResolvedValue([
      {
        id: "g1",
        name: "Multi-Currency NGO",
        country: "GB",
        budgets_count: 2,
        total_allocated_by_currency: [
          { currency: "GBP", total_allocated: 3000 },
          { currency: "USD", total_allocated: 5000 },
        ],
      },
    ]);
    getFundedBudgetsMock.mockResolvedValue([
      {
        id: "b1",
        name: "GBP Budget",
        status: "draft",
        total_amount: 3000,
        local_currency: "GBP",
        owner: { id: "g1", name: "Multi-Currency NGO" },
      },
    ]);

    renderDashboard();

    // Stat tile and grantee row both show BOTH currencies, not one blended
    // (and wrongly labeled) figure — see #139 review.
    await waitFor(() =>
      expect(screen.getAllByText("£3,000 + US$5,000").length).toBeGreaterThan(0),
    );
  });

  it("shows an empty state when the donor has zero funded budgets", async () => {
    getFundedBudgetsSummaryMock.mockResolvedValue({
      total_budgets: 0,
      total_allocated_by_currency: [],
    });
    getFundedGranteesMock.mockResolvedValue([]);
    getFundedBudgetsMock.mockResolvedValue([]);

    renderDashboard();

    await waitFor(() =>
      expect(screen.getByText("No funded budgets yet")).toBeInTheDocument(),
    );
    expect(screen.queryByText("Grantees")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "View Reports" })).not.toBeInTheDocument();
  });
});
