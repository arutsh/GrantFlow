import { render, screen } from "@testing-library/react";
import { BudgetViewTraces } from "./BudgetViewTraces";

describe("BudgetViewTraces", () => {
  it("condenses created/updated into one slim line instead of two cards", () => {
    render(
      <BudgetViewTraces
        budget={{
          trace: {
            created: {
              user: { first_name: "Jane", last_name: "Doe" },
              event_date: "2026-07-28T10:14:00Z",
            },
            updated: {
              user: { first_name: "Jane", last_name: "Doe" },
              event_date: "2026-08-02T09:02:00Z",
            },
          },
        }}
      />,
    );

    expect(screen.getByText(/Created by Jane Doe/)).toBeInTheDocument();
    expect(screen.getByText(/Updated by Jane Doe/)).toBeInTheDocument();
  });

  it("falls back to an em dash when no trace data exists", () => {
    render(<BudgetViewTraces budget={{}} />);

    expect(screen.getByText(/Created by — · —/)).toBeInTheDocument();
    expect(screen.getByText(/Updated by — · —/)).toBeInTheDocument();
  });
});
