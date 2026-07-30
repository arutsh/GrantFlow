import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { BudgetViewHeader } from "./BudgetViewHeader";
import { Budget } from "../types/budget";
import * as budgetApi from "@/api/budgetApi";
import * as roleAccess from "@/utils/roleAccess";

vi.mock("@/api/budgetApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/budgetApi")>();
  return {
    ...actual,
    editBudget: vi.fn(),
  };
});

vi.mock("@/utils/roleAccess", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/utils/roleAccess")>();
  return {
    ...actual,
    getCurrentCustomerId: vi.fn(),
    isBudgetOwner: vi.fn(),
    isBudgetFunder: vi.fn(),
  };
});

const editBudgetMock = budgetApi.editBudget as unknown as ReturnType<typeof vi.fn>;
const getCurrentCustomerIdMock = roleAccess.getCurrentCustomerId as unknown as ReturnType<
  typeof vi.fn
>;
const isBudgetOwnerMock = roleAccess.isBudgetOwner as unknown as ReturnType<typeof vi.fn>;
const isBudgetFunderMock = roleAccess.isBudgetFunder as unknown as ReturnType<typeof vi.fn>;

function makeBudget(overrides: Partial<Budget> = {}): Budget {
  return {
    id: "b1",
    name: "Clean Water Phase 1",
    status: "draft",
    owner: { id: "owner-1", name: "Hope Relief NGO" },
    funder: { id: "funder-1", name: "Donor 7" },
    duration_months: 24,
    ...overrides,
  };
}

describe("BudgetViewHeader confirm action", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    isBudgetFunderMock.mockReturnValue(false);
  });

  it("hides the Confirm Budget action once the budget is already confirmed", () => {
    render(
      <BudgetViewHeader budget={makeBudget({ status: "confirmed" })} isLocked={false} />,
    );

    expect(
      screen.queryByRole("button", { name: /confirm budget/i }),
    ).not.toBeInTheDocument();
  });

  it("hides the action for a non-owner, non-funder viewer", () => {
    isBudgetOwnerMock.mockReturnValue(false);
    isBudgetFunderMock.mockReturnValue(false);

    render(<BudgetViewHeader budget={makeBudget()} isLocked={false} />);

    expect(
      screen.queryByRole("button", { name: /confirm budget/i }),
    ).not.toBeInTheDocument();
  });

  it("shows the action to the matching funder even when they are not the owner", () => {
    isBudgetOwnerMock.mockReturnValue(false);
    isBudgetFunderMock.mockReturnValue(true);

    render(<BudgetViewHeader budget={makeBudget()} isLocked={false} />);

    expect(screen.getByRole("button", { name: /confirm budget/i })).toBeInTheDocument();
  });

  it("disables the Confirm Budget button until a start date is picked", () => {
    render(<BudgetViewHeader budget={makeBudget()} isLocked={false} />);

    expect(screen.getByRole("button", { name: /confirm budget/i })).toBeDisabled();
  });

  it("prefills the start date from budget.start_date, so re-confirming after a cancel doesn't require retyping it", () => {
    render(
      <BudgetViewHeader
        budget={makeBudget({ start_date: "2026-08-01" })}
        isLocked={false}
      />,
    );

    expect(screen.getByLabelText(/start date/i)).toHaveValue("2026-08-01");
    expect(screen.getByRole("button", { name: /confirm budget/i })).not.toBeDisabled();
  });

  it("calls editBudget with the start date and confirmed status, and reports the update", async () => {
    const user = userEvent.setup();
    const updated = makeBudget({ status: "confirmed", start_date: "2026-08-01" });
    editBudgetMock.mockResolvedValue(updated);
    const onBudgetUpdated = vi.fn();

    render(
      <BudgetViewHeader
        budget={makeBudget()}
        isLocked={false}
        onBudgetUpdated={onBudgetUpdated}
      />,
    );

    const dateInput = screen.getByLabelText(/start date/i);
    await user.type(dateInput, "2026-08-01");

    const confirmButton = screen.getByRole("button", { name: /confirm budget/i });
    expect(confirmButton).not.toBeDisabled();
    await user.click(confirmButton);

    await waitFor(() =>
      expect(editBudgetMock).toHaveBeenCalledWith("b1", {
        start_date: "2026-08-01",
        status: "confirmed",
      }),
    );
    await waitFor(() => expect(onBudgetUpdated).toHaveBeenCalledWith(updated));
  });

  it("shows an inline error and leaves the action visible when the backend rejects confirmation", async () => {
    const user = userEvent.setup();
    editBudgetMock.mockRejectedValue(new Error("rejected"));
    const onBudgetUpdated = vi.fn();

    render(
      <BudgetViewHeader
        budget={makeBudget()}
        isLocked={false}
        onBudgetUpdated={onBudgetUpdated}
      />,
    );

    const dateInput = screen.getByLabelText(/start date/i);
    await user.type(dateInput, "2026-08-01");
    await user.click(screen.getByRole("button", { name: /confirm budget/i }));

    await waitFor(() =>
      expect(screen.getByText(/failed to confirm budget/i)).toBeInTheDocument(),
    );
    expect(onBudgetUpdated).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /confirm budget/i })).toBeInTheDocument();
  });
});

describe("BudgetViewHeader status and dates", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    isBudgetFunderMock.mockReturnValue(false);
  });

  it("shows the status badge and omits dates when start_date is unset", () => {
    render(<BudgetViewHeader budget={makeBudget({ status: "draft" })} isLocked={false} />);

    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(2); // start + end date
  });

  it("shows start date, backend-computed end date, and status once confirmed", () => {
    render(
      <BudgetViewHeader
        budget={makeBudget({
          status: "confirmed",
          start_date: "2026-01-15",
          end_date: "2027-01-15",
          duration_months: 12,
        })}
        isLocked={false}
      />,
    );

    expect(screen.getByText("Confirmed")).toBeInTheDocument();
    expect(screen.getByText("15 Jan 2026")).toBeInTheDocument();
    expect(screen.getByText("15 Jan 2027")).toBeInTheDocument();
  });
});

describe("BudgetViewHeader edit lock", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    isBudgetFunderMock.mockReturnValue(false);
  });

  it("shows the Edit action when the budget is not locked", () => {
    render(
      <BudgetViewHeader budget={makeBudget({ status: "draft" })} isLocked={false} />,
    );

    expect(screen.getByRole("button", { name: "Edit" })).toBeInTheDocument();
  });

  it("hides the Edit action once the budget is locked (confirmed)", () => {
    render(
      <BudgetViewHeader budget={makeBudget({ status: "confirmed" })} isLocked={true} />,
    );

    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.getByText(/locked: confirmed/i)).toBeInTheDocument();
  });
});

describe("BudgetViewHeader cancel confirmation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    isBudgetFunderMock.mockReturnValue(false);
  });

  it("is hidden on a draft budget", () => {
    render(<BudgetViewHeader budget={makeBudget({ status: "draft" })} isLocked={false} />);

    expect(
      screen.queryByRole("button", { name: /cancel confirmation/i }),
    ).not.toBeInTheDocument();
  });

  it("is hidden from a non-owner (e.g. the matching funder) on a confirmed budget", () => {
    isBudgetOwnerMock.mockReturnValue(false);

    render(
      <BudgetViewHeader budget={makeBudget({ status: "confirmed" })} isLocked={false} />,
    );

    expect(
      screen.queryByRole("button", { name: /cancel confirmation/i }),
    ).not.toBeInTheDocument();
  });

  it("requires a second click and shows a warning before reverting", async () => {
    const user = userEvent.setup();
    const onBudgetUpdated = vi.fn();

    render(
      <BudgetViewHeader
        budget={makeBudget({ status: "confirmed" })}
        isLocked={false}
        onBudgetUpdated={onBudgetUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: /cancel confirmation/i }));

    expect(
      screen.getByText(/this will delete any draft report\(s\)/i),
    ).toBeInTheDocument();
    expect(editBudgetMock).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Yes" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "No" })).toBeInTheDocument();
  });

  it("does not revert when the warning is dismissed with No", async () => {
    const user = userEvent.setup();
    const onBudgetUpdated = vi.fn();

    render(
      <BudgetViewHeader
        budget={makeBudget({ status: "confirmed" })}
        isLocked={false}
        onBudgetUpdated={onBudgetUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: /cancel confirmation/i }));
    await user.click(screen.getByRole("button", { name: "No" }));

    expect(editBudgetMock).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /cancel confirmation/i })).toBeInTheDocument();
  });

  it("reverts the budget once the warning is confirmed with Yes", async () => {
    const user = userEvent.setup();
    const reverted = makeBudget({ status: "draft" });
    editBudgetMock.mockResolvedValue(reverted);
    const onBudgetUpdated = vi.fn();

    render(
      <BudgetViewHeader
        budget={makeBudget({ status: "confirmed" })}
        isLocked={false}
        onBudgetUpdated={onBudgetUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: /cancel confirmation/i }));
    await user.click(screen.getByRole("button", { name: "Yes" }));

    await waitFor(() =>
      expect(editBudgetMock).toHaveBeenCalledWith("b1", { status: "draft" }),
    );
    await waitFor(() => expect(onBudgetUpdated).toHaveBeenCalledWith(reverted));
  });

  it("shows the backend's rejection message when blocked by a non-draft report", async () => {
    const user = userEvent.setup();
    editBudgetMock.mockRejectedValue({
      response: {
        data: {
          detail:
            "Cannot revert to draft while the budget has a submitted, approved, or rejected report",
        },
      },
    });
    const onBudgetUpdated = vi.fn();

    render(
      <BudgetViewHeader
        budget={makeBudget({ status: "confirmed" })}
        isLocked={true}
        onBudgetUpdated={onBudgetUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: /cancel confirmation/i }));
    await user.click(screen.getByRole("button", { name: "Yes" }));

    await waitFor(() =>
      expect(
        screen.getByText(/cannot revert to draft while the budget has a submitted/i),
      ).toBeInTheDocument(),
    );
    expect(onBudgetUpdated).not.toHaveBeenCalled();
  });
});

describe("BudgetViewHeader metadata edit", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    isBudgetFunderMock.mockReturnValue(false);
  });

  it("opens ai_draft budgets straight into edit mode", () => {
    render(
      <BudgetViewHeader budget={makeBudget({ status: "ai_draft" })} isLocked={false} />,
    );

    expect(screen.getByRole("button", { name: /save changes/i })).toBeInTheDocument();
  });

  it("saves name/funder/duration without touching status or start_date", async () => {
    const user = userEvent.setup();
    const updated = makeBudget({ name: "Renamed" });
    editBudgetMock.mockResolvedValue(updated);
    const onBudgetUpdated = vi.fn();

    render(
      <BudgetViewHeader
        budget={makeBudget()}
        isLocked={false}
        onBudgetUpdated={onBudgetUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const nameInput = screen.getByDisplayValue("Clean Water Phase 1");
    await user.clear(nameInput);
    await user.type(nameInput, "Renamed");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() =>
      expect(editBudgetMock).toHaveBeenCalledWith("b1", {
        name: "Renamed",
        external_funder_name: "Donor 7",
        duration_months: 24,
      }),
    );
    await waitFor(() => expect(onBudgetUpdated).toHaveBeenCalledWith(updated));
  });
});
