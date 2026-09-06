import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { BudgetViewLinesTable } from "./BudgetViewLinesTable";
import { Budget, BudgetLine } from "../types/budget";
import * as context from "../SingleBudgetViewContext";
import * as gatewayApi from "@/api/gatewayApi";

vi.mock("../SingleBudgetViewContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../SingleBudgetViewContext")>();
  return { ...actual, useDetailedBudget: vi.fn() };
});

vi.mock("@/api/gatewayApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/gatewayApi")>();
  return { ...actual, updateBudgetCategory: vi.fn() };
});

const useDetailedBudgetMock = context.useDetailedBudget as unknown as Mock;
const updateBudgetCategoryMock = gatewayApi.updateBudgetCategory as unknown as Mock;

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
      [makeLine({ id: "bl1", amount: 400, category: { id: "c1", name: "Coordinator", code: "COORD", budget_id: "b1" } })],
      { bl1: 400 },
    );

    const pills = screen.getAllByText("100%");
    expect(pills.length).toBeGreaterThan(0);
    expect(pills[0].className).toContain("bg-green-100");
    expect(screen.getAllByText("£400 / £400").length).toBeGreaterThan(0);
  });

  it("shows an amber pill when a line is only partially reported", () => {
    renderTable(
      [makeLine({ id: "bl2", amount: 200, category: { id: "c2", name: "IT", code: "IT", budget_id: "b1" } })],
      { bl2: 50 },
    );

    const pills = screen.getAllByText("25%");
    expect(pills[0].className).toContain("bg-amber-100");
    expect(screen.getAllByText("£50 / £200").length).toBeGreaterThan(0);
  });

  it("shows a red pill when a line's reported spend exceeds its allocation", () => {
    renderTable(
      [makeLine({ id: "bl3", amount: 100, category: { id: "c3", name: "Travel", code: "TRV", budget_id: "b1" } })],
      { bl3: 150 },
    );

    const pills = screen.getAllByText("150%");
    expect(pills[0].className).toContain("bg-red-100");
  });

  it("shows a neutral pill when nothing has been reported against a line yet", () => {
    renderTable(
      [makeLine({ id: "bl4", amount: 300, category: { id: "c4", name: "Misc", code: "MISC", budget_id: "b1" } })],
      {},
    );

    const pills = screen.getAllByText("0%");
    expect(pills[0].className).toContain("bg-slate-100");
    expect(screen.getAllByText("£0 / £300").length).toBeGreaterThan(0);
  });

  it("shows a loading pill instead of 0% while spend is still being fetched (#216)", () => {
    renderTable(
      [makeLine({ id: "bl5", amount: 300, category: { id: "c5", name: "Misc", code: "MISC", budget_id: "b1" } })],
      {},
      {},
      true,
    );

    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    const pills = screen.getAllByText("…");
    expect(pills.length).toBeGreaterThan(0);
    expect(screen.getAllByText("Loading…").length).toBeGreaterThan(0);
  });

  it("shows the group subtotal's Used percentage in Both mode instead of a dash", async () => {
    const user = userEvent.setup();
    renderTable(
      [makeLine({ id: "bl1", amount: 1000, category: { id: "c1", name: "Category1", code: "CAT1", budget_id: "b1" } })],
      { bl1: 0 },
      { actual_currency: "USD", estimated_exchange_rate: 0.8 },
    );

    await user.click(screen.getByRole("button", { name: "Both" }));

    const table = screen.getByRole("table");
    expect(within(table).getAllByText("0%").length).toBeGreaterThan(0);
    expect(within(table).queryByText("—")).not.toBeInTheDocument();
  });
});

describe("BudgetViewLinesTable mobile card list", () => {
  it("groups lines by category with a subtotal, mirroring the desktop table's grouping", () => {
    renderTable(
      [
        makeLine({ id: "bl1", description: "Salary", amount: 400, category: { id: "c1", name: "Staff costs", code: "STAFF", budget_id: "b1" } }),
        makeLine({ id: "bl2", description: "Stipend", amount: 100, category: { id: "c1", name: "Staff costs", code: "STAFF", budget_id: "b1" } }),
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
          lines={[makeLine({ id: "bl1", category: { id: "c1", name: "Misc", code: "MISC", budget_id: "b1" } })]}
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
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF", budget_id: "b1" } })],
      { bl1: 400 },
    );

    expect(screen.queryByRole("group", { name: /currency display/i })).not.toBeInTheDocument();
    expect(screen.getAllByText("£800").length).toBeGreaterThan(0);
  });

  it("shows the toggle when the budget has an estimated_exchange_rate", () => {
    renderTable(
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF", budget_id: "b1" } })],
      { bl1: 400 },
      { actual_currency: "EUR", estimated_exchange_rate: 0.8 },
    );

    expect(screen.getByRole("group", { name: /currency display/i })).toBeInTheDocument();
  });

  it("labels Amount/Used with the currency in the column header instead of repeating it inline", () => {
    renderTable(
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF", budget_id: "b1" } })],
      { bl1: 400 },
      { actual_currency: "EUR", estimated_exchange_rate: 0.8 },
    );

    expect(screen.getByText("Amount (GBP)")).toBeInTheDocument();
    expect(screen.getByText("Used")).toBeInTheDocument();
  });

  it("converts Amount and Used to the donor currency when Donor (estimated) is selected, stating the currency once in the header", async () => {
    const user = userEvent.setup();
    renderTable(
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF", budget_id: "b1" } })],
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
      [makeLine({ id: "bl1", amount: 800, category: { id: "c1", name: "Staff", code: "STAFF", budget_id: "b1" } })],
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

describe("BudgetViewLinesTable Grouped/Simple toggle", () => {
  const groupedLines = [
    makeLine({ id: "bl1", description: "Salary", amount: 400, category: { id: "c1", name: "Staff costs", code: "STAFF", budget_id: "b1" } }),
    makeLine({ id: "bl2", description: "Stipend", amount: 100, category: { id: "c1", name: "Staff costs", code: "STAFF", budget_id: "b1" } }),
  ];

  it("defaults to Grouped, showing a category subtotal row on desktop", () => {
    renderTable(groupedLines, { bl1: 0, bl2: 0 });

    const table = screen.getByRole("table");
    expect(within(table).getByText("Staff costs")).toBeInTheDocument();
    expect(within(table).getAllByText(/Subtotal:/).length).toBeGreaterThan(0);
  });

  it("exposes the toggle as a labeled group", () => {
    renderTable(groupedLines, { bl1: 0, bl2: 0 });
    expect(screen.getByRole("group", { name: /grouping display/i })).toBeInTheDocument();
  });

  it("switches to Simple, showing a flat list with no subtotal rows", async () => {
    const user = userEvent.setup();
    renderTable(groupedLines, { bl1: 0, bl2: 0 });

    await user.click(screen.getByRole("button", { name: "Simple" }));

    const table = screen.getByRole("table");
    expect(within(table).queryByText(/Subtotal:/)).not.toBeInTheDocument();
    expect(within(table).getByText("Salary")).toBeInTheDocument();
    expect(within(table).getByText("Stipend")).toBeInTheDocument();
  });

  it("switching back to Grouped restores subtotal rows", async () => {
    const user = userEvent.setup();
    renderTable(groupedLines, { bl1: 0, bl2: 0 });

    await user.click(screen.getByRole("button", { name: "Simple" }));
    await user.click(screen.getByRole("button", { name: "Grouped" }));

    const table = screen.getByRole("table");
    expect(within(table).getAllByText(/Subtotal:/).length).toBeGreaterThan(0);
  });

  it("leaves mobile grouping unaffected when desktop switches to Simple", async () => {
    const user = userEvent.setup();
    renderTable(groupedLines, { bl1: 0, bl2: 0 });

    // One "(2)" badge from the desktop group header, one from the mobile card header.
    expect(screen.getAllByText("(2)").length).toBe(2);

    await user.click(screen.getByRole("button", { name: "Simple" }));

    // Desktop ungroups (its badge disappears); mobile's stays.
    expect(screen.getAllByText("(2)").length).toBe(1);
  });
});

describe("BudgetViewLinesTable category rename", () => {
  function renderTableWithSetBudget(
    lines: BudgetLine[],
    readOnly = false,
  ) {
    const setBudgetMock = vi.fn();
    useDetailedBudgetMock.mockReturnValue({
      budget: makeBudget({ lines }),
      setBudget: setBudgetMock,
      budgetCategories: [],
      budgetCategoryNames: [],
      existingExtraKeys: [],
      spendByLineId: {},
      isSpendPending: false,
    });
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    render(
      <QueryClientProvider client={queryClient}>
        <BudgetViewLinesTable
          lines={lines}
          onEdit={vi.fn()}
          onNew={vi.fn()}
          onClose={vi.fn()}
          readOnly={readOnly}
        />
      </QueryClientProvider>,
    );
    return { setBudgetMock };
  }

  beforeEach(() => {
    updateBudgetCategoryMock.mockReset();
  });

  it("shows the rename pencil on desktop and mobile only for a real category", () => {
    const lines = [
      makeLine({ id: "bl1", category: { id: "c1", name: "Travel", code: "TRV", budget_id: "b1" } }),
      makeLine({ id: "bl2" }),
    ];
    renderTableWithSetBudget(lines);

    expect(screen.getAllByTitle("Rename category").length).toBe(2);
  });

  it("loses the desktop rename pencil in Simple view but keeps the mobile one", async () => {
    const user = userEvent.setup();
    const lines = [makeLine({ id: "bl1", category: { id: "c1", name: "Travel", code: "TRV", budget_id: "b1" } })];
    renderTableWithSetBudget(lines);

    expect(screen.getAllByTitle("Rename category").length).toBe(2);

    await user.click(screen.getByRole("button", { name: "Simple" }));

    expect(screen.getAllByTitle("Rename category").length).toBe(1);
  });

  it("hides the rename pencil entirely on a read-only budget", () => {
    const lines = [makeLine({ id: "bl1", category: { id: "c1", name: "Travel", code: "TRV", budget_id: "b1" } })];
    renderTableWithSetBudget(lines, true);

    expect(screen.queryByTitle("Rename category")).not.toBeInTheDocument();
  });

  it("confirming a rename submits the PATCH and reflects the new name via setBudget", async () => {
    const user = userEvent.setup();
    updateBudgetCategoryMock.mockResolvedValueOnce({ id: "c1", name: "Transport", code: "TRV", budget_id: "b1" });
    const lines = [makeLine({ id: "bl1", category: { id: "c1", name: "Travel", code: "TRV", budget_id: "b1" } })];
    const { setBudgetMock } = renderTableWithSetBudget(lines);

    await user.click(screen.getAllByTitle("Rename category")[0]);
    const input = screen.getByRole("textbox");
    await user.clear(input);
    await user.type(input, "Transport");
    await user.keyboard("{Enter}");

    await waitFor(() => {
      expect(updateBudgetCategoryMock).toHaveBeenCalledWith("c1", { name: "Transport" });
    });
    await waitFor(() => expect(setBudgetMock).toHaveBeenCalled());
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  it("Escape cancels a rename without sending a request", async () => {
    const user = userEvent.setup();
    const lines = [makeLine({ id: "bl1", category: { id: "c1", name: "Travel", code: "TRV", budget_id: "b1" } })];
    renderTableWithSetBudget(lines);

    await user.click(screen.getAllByTitle("Rename category")[0]);
    await user.type(screen.getByRole("textbox"), "X");
    await user.keyboard("{Escape}");

    expect(updateBudgetCategoryMock).not.toHaveBeenCalled();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    expect(screen.getAllByText("Travel").length).toBeGreaterThan(0);
  });

  it("surfaces a duplicate-name rejection inline and leaves the name unchanged", async () => {
    const user = userEvent.setup();
    updateBudgetCategoryMock.mockRejectedValueOnce({
      response: { data: { detail: "A category with this name already exists" } },
    });
    const lines = [makeLine({ id: "bl1", category: { id: "c1", name: "Travel", code: "TRV", budget_id: "b1" } })];
    renderTableWithSetBudget(lines);

    await user.click(screen.getAllByTitle("Rename category")[0]);
    const input = screen.getByRole("textbox");
    await user.clear(input);
    await user.type(input, "Duplicate");
    await user.keyboard("{Enter}");

    await screen.findByText("A category with this name already exists");
    expect(screen.getByRole("textbox")).toHaveValue("Duplicate");
    expect(screen.getAllByText("Travel").length).toBeGreaterThan(0);
  });
});
