import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { BudgetViewLinesTable } from "./BudgetViewLinesTable";
import { Budget, BudgetLine } from "../types/budget";
import * as context from "../SingleBudgetViewContext";

vi.mock("../SingleBudgetViewContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../SingleBudgetViewContext")>();
  return { ...actual, useDetailedBudget: vi.fn() };
});

const useDetailedBudgetMock = context.useDetailedBudget as unknown as Mock;

function makeBudget(overrides: Partial<Budget> = {}): Budget {
  return { id: "b1", name: "Demo budget", status: "confirmed", local_currency: "GBP", ...overrides };
}

function makeLine(overrides: Partial<BudgetLine> = {}): BudgetLine {
  return { id: "bl1", budget_id: "b1", description: "Line", amount: 100, ...overrides };
}

function renderTable(lines: BudgetLine[], spendByLineId: Record<string, number>) {
  useDetailedBudgetMock.mockReturnValue({
    budget: makeBudget(),
    setBudget: vi.fn(),
    budgetCategories: [],
    budgetCategoryNames: [],
    existingExtraKeys: [],
    spendByLineId,
  });
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <BudgetViewLinesTable
        lines={lines}
        onEdit={vi.fn()}
        onNew={vi.fn()}
        onClose={vi.fn()}
      />
    </QueryClientProvider>,
  );
}

describe("BudgetViewLinesTable Used column", () => {
  it("shows a green 100% pill when a line's reported spend exactly matches its allocation", () => {
    renderTable(
      [makeLine({ id: "bl1", amount: 400, category: { id: "c1", name: "Coordinator", code: "COORD" } })],
      { bl1: 400 },
    );

    const pill = screen.getByText("100%");
    expect(pill).toBeInTheDocument();
    expect(pill.className).toContain("bg-green-100");
    expect(screen.getByText("£400 / £400")).toBeInTheDocument();
  });

  it("shows an amber pill when a line is only partially reported", () => {
    renderTable(
      [makeLine({ id: "bl2", amount: 200, category: { id: "c2", name: "IT", code: "IT" } })],
      { bl2: 50 },
    );

    const pill = screen.getByText("25%");
    expect(pill.className).toContain("bg-amber-100");
    expect(screen.getByText("£50 / £200")).toBeInTheDocument();
  });

  it("shows a red pill when a line's reported spend exceeds its allocation", () => {
    renderTable(
      [makeLine({ id: "bl3", amount: 100, category: { id: "c3", name: "Travel", code: "TRV" } })],
      { bl3: 150 },
    );

    const pill = screen.getByText("150%");
    expect(pill.className).toContain("bg-red-100");
  });

  it("shows a neutral pill when nothing has been reported against a line yet", () => {
    renderTable(
      [makeLine({ id: "bl4", amount: 300, category: { id: "c4", name: "Misc", code: "MISC" } })],
      {},
    );

    const pill = screen.getByText("0%");
    expect(pill.className).toContain("bg-slate-100");
    expect(screen.getByText("£0 / £300")).toBeInTheDocument();
  });
});
