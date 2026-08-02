import { render, screen } from "@testing-library/react";
import { vi, type Mock } from "vitest";
import { BudgetViewSummary } from "./BudgetViewSummary";
import { Budget } from "../types/budget";
import * as context from "../SingleBudgetViewContext";

vi.mock("../SingleBudgetViewContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../SingleBudgetViewContext")>();
  return { ...actual, useDetailedBudget: vi.fn() };
});

const useDetailedBudgetMock = context.useDetailedBudget as unknown as Mock;

function makeBudget(overrides: Partial<Budget> = {}): Budget {
  return {
    id: "b1",
    name: "Demo budget",
    status: "confirmed",
    local_currency: "GBP",
    lines: [
      { id: "bl1", budget_id: "b1", description: "Coordinator Fee", amount: 1000 },
      { id: "bl2", budget_id: "b1", description: "IT Equipment", amount: 1200 },
    ],
    ...overrides,
  };
}

describe("BudgetViewSummary", () => {
  it("shows the Total Amount as the hero figure", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      totalAmount: 2200,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("Total amount")).toBeInTheDocument();
    expect(screen.getByText("£2,200")).toBeInTheDocument();
  });

  it("shows line count and categories as a small caption, not equal-weight stat tiles", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      totalAmount: 2200,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("lines")).toBeInTheDocument();
  });

  it("shows Total Reported and its percentage when at least one report exists", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      totalAmount: 2200,
      totalReported: 550,
      hasReports: true,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("Total Reported")).toBeInTheDocument();
    expect(screen.getByText("£550")).toBeInTheDocument();
    expect(screen.getByText("25% of budget")).toBeInTheDocument();
  });

  it("shows 0% of budget when a report exists but nothing has been reported yet", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      totalAmount: 2200,
      totalReported: 0,
      hasReports: true,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("Total Reported")).toBeInTheDocument();
    expect(screen.getByText("0% of budget")).toBeInTheDocument();
  });

  it("hides Total Reported entirely when no reports exist yet", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      totalAmount: 2200,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.queryByText("Total Reported")).not.toBeInTheDocument();
  });

  it("shows the donor commitment and estimated local cap when estimated_local_cap is set", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget({
        donor_total_amount: 10000,
        estimated_exchange_rate: 0.8,
        estimated_local_cap: 8000,
        actual_currency: "EUR",
      }),
      totalAmount: 2200,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("€10,000")).toBeInTheDocument();
    expect(
      screen.getByText("donor commitment @ 0.8 est. → £8,000 local cap"),
    ).toBeInTheDocument();
  });

  it("falls back to today's local-only display when estimated_local_cap is null", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget({ donor_total_amount: 10000 }),
      totalAmount: 2200,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.queryByText("€10,000")).not.toBeInTheDocument();
    expect(screen.queryByText(/donor commitment/)).not.toBeInTheDocument();
  });

  it("flags the total amount green and 'on target' when within tolerance of the cap", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget({
        donor_total_amount: 10000,
        estimated_exchange_rate: 0.8,
        estimated_local_cap: 8000,
        actual_currency: "EUR",
      }),
      totalAmount: 8100,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("£8,100")).toHaveClass("text-green-600");
    expect(screen.getByText("on target")).toBeInTheDocument();
  });

  it("flags the total amount amber and shows the shortfall when meaningfully below the cap", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget({
        donor_total_amount: 10000,
        estimated_exchange_rate: 0.8,
        estimated_local_cap: 8000,
        actual_currency: "EUR",
      }),
      totalAmount: 7000,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("£7,000")).toHaveClass("text-amber-600");
    expect(screen.getByText("13% under cap")).toBeInTheDocument();
  });

  it("flags the total amount red and shows the overage when meaningfully above the cap", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget({
        donor_total_amount: 10000,
        estimated_exchange_rate: 0.8,
        estimated_local_cap: 8000,
        actual_currency: "EUR",
      }),
      totalAmount: 8500,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("£8,500")).toHaveClass("text-red-600");
    expect(screen.getByText("6% over cap")).toBeInTheDocument();
  });

  it("does not show an allocation badge when there is no donor estimate to compare against", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      totalAmount: 2200,
      totalReported: 0,
      hasReports: false,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("£2,200")).toHaveClass("text-slate-900");
    expect(screen.queryByText(/on target|over cap|under cap/)).not.toBeInTheDocument();
  });
});
