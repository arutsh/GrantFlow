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

describe("BudgetViewHeader currency-only edit via editTrigger", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    isBudgetFunderMock.mockReturnValue(false);
  });

  it("opens a currency-only form on a locked budget and saves only actual_currency", async () => {
    const user = userEvent.setup();
    const budget = makeBudget({ status: "confirmed", actual_currency: undefined });
    editBudgetMock.mockResolvedValue(makeBudget({ status: "confirmed", actual_currency: "USD" }));
    const onBudgetUpdated = vi.fn();

    const { rerender } = render(
      <BudgetViewHeader budget={budget} isLocked onBudgetUpdated={onBudgetUpdated} />,
    );
    rerender(
      <BudgetViewHeader
        budget={budget}
        isLocked
        onBudgetUpdated={onBudgetUpdated}
        editTrigger={1}
      />,
    );

    // Name/funder/duration stay read-only text, not inputs — only currency
    // is editable while the budget is locked.
    expect(screen.queryByDisplayValue("Clean Water Phase 1")).not.toBeInTheDocument();
    expect(screen.getByText("Clean Water Phase 1")).toBeInTheDocument();
    expect(screen.getByText(/only the actual currency can be updated/i)).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox"), "USD");
    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() =>
      expect(editBudgetMock).toHaveBeenCalledWith("b1", { actual_currency: "USD" }),
    );
    await waitFor(() => expect(onBudgetUpdated).toHaveBeenCalled());
  });

  it("still opens the full edit form via editTrigger when the budget is not locked", async () => {
    const budget = makeBudget({ status: "draft" });

    const { rerender } = render(<BudgetViewHeader budget={budget} isLocked={false} />);
    rerender(<BudgetViewHeader budget={budget} isLocked={false} editTrigger={1} />);

    expect(screen.getByDisplayValue("Clean Water Phase 1")).toBeInTheDocument();
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
        // Sent as explicit null (not omitted) since the budget never had
        // these set — same as the user clearing them — so the backend
        // reads it as "no commitment", not "leave untouched".
        donor_total_amount: null,
        estimated_exchange_rate: null,
      }),
    );
    await waitFor(() => expect(onBudgetUpdated).toHaveBeenCalledWith(updated));
  });

  it("shows editable donor commitment and estimated rate fields and saves them", async () => {
    const user = userEvent.setup();
    const updated = makeBudget({ donor_total_amount: 10000, estimated_exchange_rate: 0.8 });
    editBudgetMock.mockResolvedValue(updated);
    const onBudgetUpdated = vi.fn();

    render(
      <BudgetViewHeader
        budget={makeBudget({ actual_currency: "EUR" })}
        isLocked={false}
        onBudgetUpdated={onBudgetUpdated}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));

    const donorInput = screen.getByText(/donor commitment/i).parentElement!.querySelector(
      "input",
    ) as HTMLInputElement;
    const rateInput = screen.getByText(/estimated rate/i).parentElement!.querySelector(
      "input",
    ) as HTMLInputElement;
    await user.type(donorInput, "10000");
    await user.type(rateInput, "0.8");

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() =>
      expect(editBudgetMock).toHaveBeenCalledWith(
        "b1",
        expect.objectContaining({ donor_total_amount: 10000, estimated_exchange_rate: 0.8 }),
      ),
    );
    await waitFor(() => expect(onBudgetUpdated).toHaveBeenCalledWith(updated));
  });

  it("sends explicit null when an existing donor commitment/rate is cleared, so the backend actually clears it", async () => {
    const user = userEvent.setup();
    const updated = makeBudget({ donor_total_amount: null, estimated_exchange_rate: null });
    editBudgetMock.mockResolvedValue(updated);

    render(
      <BudgetViewHeader
        budget={makeBudget({
          actual_currency: "EUR",
          donor_total_amount: 10000,
          estimated_exchange_rate: 0.8,
        })}
        isLocked={false}
        onBudgetUpdated={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));

    const donorInput = screen.getByText(/donor commitment/i).parentElement!.querySelector(
      "input",
    ) as HTMLInputElement;
    const rateInput = screen.getByText(/estimated rate/i).parentElement!.querySelector(
      "input",
    ) as HTMLInputElement;
    await user.clear(donorInput);
    await user.clear(rateInput);

    await user.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() =>
      expect(editBudgetMock).toHaveBeenCalledWith(
        "b1",
        expect.objectContaining({ donor_total_amount: null, estimated_exchange_rate: null }),
      ),
    );
  });

  it("disables Save and shows an error when the estimated rate is zero or negative", async () => {
    const user = userEvent.setup();

    render(
      <BudgetViewHeader
        budget={makeBudget({ actual_currency: "EUR" })}
        isLocked={false}
        onBudgetUpdated={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Edit" }));
    const rateInput = screen.getByText(/estimated rate/i).parentElement!.querySelector(
      "input",
    ) as HTMLInputElement;
    await user.type(rateInput, "0");

    expect(screen.getByText("Must be greater than zero.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /save changes/i })).toBeDisabled();
  });

  it("shows donor commitment and estimated rate as read-only text, not inputs, during a currency-only edit", () => {
    const budget = makeBudget({
      status: "confirmed",
      donor_total_amount: 10000,
      estimated_exchange_rate: 0.8,
      actual_currency: "EUR",
    });

    const { rerender } = render(
      <BudgetViewHeader budget={budget} isLocked onBudgetUpdated={vi.fn()} />,
    );
    rerender(
      <BudgetViewHeader budget={budget} isLocked onBudgetUpdated={vi.fn()} editTrigger={1} />,
    );

    expect(screen.getByText("10000 EUR")).toBeInTheDocument();
    expect(screen.getByText("0.8")).toBeInTheDocument();
  });
});
