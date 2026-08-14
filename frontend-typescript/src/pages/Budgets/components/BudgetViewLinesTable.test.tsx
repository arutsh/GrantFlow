import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

function renderTable(
  lines: BudgetLine[],
  spendByLineId: Record<string, number>,
  budgetOverrides: Partial<Budget> = {},
  isSpendPending = false,
) {
  useDetailedBudgetMock.mockReturnValue({
    budget: makeBudget(budgetOverrides),
    setBudget: vi.fn(),
    budgetCategories: [],
    budgetCategoryNames: [],
    existingExtraKeys: [],
    spendByLineId,
    isSpendPending,
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
  // Every assertion below uses getAllByText/getAllByRole rather than the
  // singular getBy* form: the component now renders both a desktop table
  // (hidden sm:block) and a mobile card list (sm:hidden) at once — CSS
  // decides which is visible, but jsdom has no viewport, so both exist in
  // the DOM, and single-line fixtures also duplicate the mobile category
  // header's aggregated pill (subtotal == the one line's amount).
  it("shows a green 100% pill when a line's reported spend exactly matches its allocation", () => {
    renderTable(
      [makeLine({ id: "bl1", amount: 400, category: { id: "c1", name: "Coordinator", code: "COORD" } })],
      { bl1: 400 },
    );

    const pills = screen.getAllByText("100%");
    expect(pills.length).toBeGreaterThan(0);
    expect(pills[0].className).toContain("bg-green-100");
    expect(screen.getAllByText("£400 / £400").length).toBeGreaterThan(0);
  });

  it("shows an amber pill when a line is only partially reported", () => {
    renderTable(
      [makeLine({ id: "bl2", amount: 200, category: { id: "c2", name: "IT", code: "IT" } })],
      { bl2: 50 },
    );

    const pills = screen.getAllByText("25%");
    expect(pills[0].className).toContain("bg-amber-100");
    expect(screen.getAllByText("£50 / £200").length).toBeGreaterThan(0);
  });

  it("shows a red pill when a line's reported spend exceeds its allocation", () => {
    renderTable(
      [makeLine({ id: "bl3", amount: 100, category: { id: "c3", name: "Travel", code: "TRV" } })],
      { bl3: 150 },
    );

    const pills = screen.getAllByText("150%");
    expect(pills[0].className).toContain("bg-red-100");
  });

  it("shows a neutral pill when nothing has been reported against a line yet", () => {
    renderTable(
      [makeLine({ id: "bl4", amount: 300, category: { id: "c4", name: "Misc", code: "MISC" } })],
      {},
    );

    const pills = screen.getAllByText("0%");
    expect(pills[0].className).toContain("bg-slate-100");
    expect(screen.getAllByText("£0 / £300").length).toBeGreaterThan(0);
  });

  it("shows a loading pill instead of 0% while spend is still being fetched (#216)", () => {
    renderTable(
      [makeLine({ id: "bl5", amount: 300, category: { id: "c5", name: "Misc", code: "MISC" } })],
      {},
      {},
      true,
    );

    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    const pills = screen.getAllByText("…");
    expect(pills.length).toBeGreaterThan(0);
    expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0);
  });
});

describe("BudgetViewLinesTable mobile card list", () => {
  it("groups lines by category with a subtotal, mirroring the desktop table's grouping", () => {
    renderTable(
      [
        makeLine({ id: "bl1", description: "Salary", amount: 400, category: { id: "c1", name: "Staff costs", code: "STAFF" } }),
        makeLine({ id: "bl2", description: "Stipend", amount: 100, category: { id: "c1", name: "Staff costs", code: "STAFF" } }),
      ],
      { bl1: 400, bl2: 0 },
    );

    expect(screen.getAllByText(/Staff costs/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("(2)").length).toBeGreaterThan(0);
    expect(screen.getAllByText("£500").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Salary").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Stipend").length).toBeGreaterThan(0);
  });

  it("hides edit/delete actions in the mobile cards when readOnly", () => {
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget(),
      setBudget: vi.fn(),
      budgetCategories: [],
      budgetCategoryNames: [],
      existingExtraKeys: [],
      spendByLineId: {},
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <BudgetViewLinesTable
          lines={[makeLine({ id: "bl1", category: { id: "c1", name: "Misc", code: "MISC" } })]}
          onEdit={vi.fn()}
          onNew={vi.fn()}
          onClose={vi.fn()}
          readOnly
        />
      </QueryClientProvider>,
    );

    expect(screen.queryByTitle("Edit line")).not.toBeInTheDocument();
    expect(screen.queryByTitle("Delete line")).not.toBeInTheDocument();
  });

  it("shows an empty state when there are no lines", () => {
    renderTable([], {});
    expect(screen.getByText("No budget lines yet.")).toBeInTheDocument();
  });
});

describe("BudgetViewLinesTable currency toggle", () => {
  it("hides the toggle when the budget has no estimated_exchange_rate", () => {
    renderTable(
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF" } })],
      { bl1: 400 },
    );

    expect(screen.queryByRole("group", { name: /currency display/i })).not.toBeInTheDocument();
    expect(screen.getAllByText("£800").length).toBeGreaterThan(0);
  });

  it("shows the toggle when the budget has an estimated_exchange_rate", () => {
    renderTable(
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF" } })],
      { bl1: 400 },
      { actual_currency: "EUR", estimated_exchange_rate: 0.8 },
    );

    expect(screen.getByRole("group", { name: /currency display/i })).toBeInTheDocument();
  });

  it("labels Amount/Used with the currency in the column header instead of repeating it inline", () => {
    renderTable(
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF" } })],
      { bl1: 400 },
      { actual_currency: "EUR", estimated_exchange_rate: 0.8 },
    );

    expect(screen.getByText("Amount (GBP)")).toBeInTheDocument();
    expect(screen.getByText("Used")).toBeInTheDocument();
  });

  it("converts Amount and Used to the donor currency when Donor (estimated) is selected, stating the currency once in the header", async () => {
    const user = userEvent.setup();
    renderTable(
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF" } })],
      { bl1: 400 },
      { actual_currency: "EUR", estimated_exchange_rate: 0.8 },
    );

    await user.click(screen.getByRole("button", { name: "Donor (estimated)" }));

    expect(screen.getByText("Amount (EUR est.)")).toBeInTheDocument();
    expect(screen.getByText("Used (EUR est.)")).toBeInTheDocument();
    // The desktop table cell doesn't repeat "(est.)" per row — only the
    // mobile card fallback (no persistent header) still does.
    const table = screen.getByRole("table");
    expect(within(table).getAllByText(/€1,000/).length).toBeGreaterThan(0);
    expect(within(table).queryByText("€1,000 (est.)")).not.toBeInTheDocument();
    // Mobile cards keep the inline label since they have no column header.
    expect(screen.getAllByText("€1,000 (est.)").length).toBeGreaterThan(0);
  });

  it("splits Amount into two real columns — one per currency — when Both is selected", async () => {
    const user = userEvent.setup();
    renderTable(
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF" } })],
      { bl1: 0 },
      { actual_currency: "EUR", estimated_exchange_rate: 0.8 },
    );

    await user.click(screen.getByRole("button", { name: "Both" }));

    expect(screen.getByText("Amount (GBP)")).toBeInTheDocument();
    expect(screen.getByText("Amount (EUR est.)")).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getAllByText(/£800/).length).toBeGreaterThan(0);
    expect(within(table).getAllByText(/€1,000/).length).toBeGreaterThan(0);

    expect(screen.getAllByText(/£800/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/€1,000 \(est\.\)/).length).toBeGreaterThan(0);
  });
});
