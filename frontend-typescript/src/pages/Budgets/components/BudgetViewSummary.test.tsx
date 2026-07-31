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
  it("shows Total Reported and its percentage of the budget", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      totalAmount: 2200,
      totalReported: 550,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("Total Reported")).toBeInTheDocument();
    expect(screen.getByText("£550")).toBeInTheDocument();
    expect(screen.getByText("25% of budget")).toBeInTheDocument();
  });

  it("shows 0% of budget when nothing has been reported yet", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      totalAmount: 2200,
      totalReported: 0,
    });

    render(<BudgetViewSummary />);

    expect(screen.getByText("0% of budget")).toBeInTheDocument();
  });
});
