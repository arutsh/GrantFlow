import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { TableView } from "./TableView";

function makeBudget(overrides: Partial<any> = {}) {
  return {
    id: "b1",
    status: "draft",
    name: "Demo budget",
    funder: { name: "Acme Foundation" },
    total_amount: 1000,
    duration_months: 6,
    local_currency: "GBP",
    trace: { updated: { event_date: "2026-01-01T00:00:00Z", user: { first_name: "A", last_name: "B" } } },
    ...overrides,
  };
}

// Regression guard: this table has no category column, so it must pass
// grouping={[]} or TanStack errors on TableCommon's ["category"] default.
describe("TableView", () => {
  it("renders the budgets list without a category column and no console errors", () => {
    const errorSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    render(
      <TableView
        data={[makeBudget()]}
        onEdit={vi.fn()}
        onDelete={vi.fn()}
        onRestore={vi.fn()}
      />,
    );

    expect(screen.getByText("Demo budget")).toBeInTheDocument();
    expect(errorSpy).not.toHaveBeenCalledWith(
      expect.stringContaining("Column with id 'category' does not exist"),
    );
    errorSpy.mockRestore();
  });
});
