import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import ReportDetailView from "./ReportDetailView";
import { Budget, Report, ReportLine } from "./types/budget";
import * as gatewayApi from "@/api/gatewayApi";
import * as reportApi from "@/api/reportApi";
import * as roleAccess from "@/utils/roleAccess";

vi.mock("@/api/gatewayApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/gatewayApi")>();
  return {
    ...actual,
    fetchBudgetById: vi.fn(),
  };
});

vi.mock("@/api/reportApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/reportApi")>();
  return {
    ...actual,
    getReport: vi.fn(),
    listReportLinesByReport: vi.fn(),
    createReportLine: vi.fn(),
    updateReportLine: vi.fn(),
    deleteReportLine: vi.fn(),
    submitReport: vi.fn(),
    reviewReport: vi.fn(),
    reopenReport: vi.fn(),
    listAttachmentsByReportLine: vi.fn(),
    uploadAttachment: vi.fn(),
    deleteAttachment: vi.fn(),
    downloadAttachment: vi.fn(),
  };
});

vi.mock("@/utils/roleAccess", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/utils/roleAccess")>();
  return {
    ...actual,
    getCurrentCustomerId: vi.fn(),
    isBudgetOwner: vi.fn(),
    canReviewReport: vi.fn(),
  };
});

const fetchBudgetByIdMock = gatewayApi.fetchBudgetById as unknown as Mock;
const getReportMock = reportApi.getReport as unknown as Mock;
const listReportLinesByReportMock = reportApi.listReportLinesByReport as unknown as Mock;
const createReportLineMock = reportApi.createReportLine as unknown as Mock;
const updateReportLineMock = reportApi.updateReportLine as unknown as Mock;
const deleteReportLineMock = reportApi.deleteReportLine as unknown as Mock;
const submitReportMock = reportApi.submitReport as unknown as Mock;
const reviewReportMock = reportApi.reviewReport as unknown as Mock;
const reopenReportMock = reportApi.reopenReport as unknown as Mock;
const listAttachmentsByReportLineMock = reportApi.listAttachmentsByReportLine as unknown as Mock;
const getCurrentCustomerIdMock = roleAccess.getCurrentCustomerId as unknown as Mock;
const isBudgetOwnerMock = roleAccess.isBudgetOwner as unknown as Mock;
const canReviewReportMock = roleAccess.canReviewReport as unknown as Mock;

function makeBudget(overrides: Partial<Budget> = {}): Budget {
  return {
    id: "b1",
    name: "Clean Water Phase 1",
    status: "confirmed",
    local_currency: "GBP",
    lines: [{ id: "bl1", budget_id: "b1", description: "Fuel budget", amount: 1000 }],
    ...overrides,
  };
}

function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    id: "r1",
    budget_id: "b1",
    name: "Q1 Report",
    status: "submitted",
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    ...overrides,
  };
}

function makeLine(overrides: Partial<ReportLine> = {}): ReportLine {
  return {
    id: "rl1",
    report_id: "r1",
    budget_line_id: "bl1",
    description: "Fuel receipts",
    amount: 250,
    expense_date: "2026-02-10",
    ...overrides,
  };
}

function renderDetail() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/budgets/b1/reports/r1"]}>
        <Routes>
          <Route path="/budgets/:id/reports/:reportId" element={<ReportDetailView />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ReportDetailView metadata and read-only lines", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    fetchBudgetByIdMock.mockResolvedValue(makeBudget());
    getCurrentCustomerIdMock.mockReturnValue(null);
    isBudgetOwnerMock.mockReturnValue(false);
    canReviewReportMock.mockReturnValue(false);
  });

  it("renders the report's name, status, period, and its lines read-only for a non-owner/non-reviewer", async () => {
    getReportMock.mockResolvedValue({ ...makeReport(), lines: [] });
    listReportLinesByReportMock.mockResolvedValue([makeLine()]);

    renderDetail();

    await waitFor(() => expect(screen.getByText("Q1 Report")).toBeInTheDocument());
    expect(screen.getByText("Submitted")).toBeInTheDocument();
    expect(screen.getByText("01 Jan 2026 – 31 Mar 2026")).toBeInTheDocument();
    expect(screen.getByText("Fuel receipts")).toBeInTheDocument();
    // Appears twice: once as the line's own amount, once as the Report
    // Summary's Total Amount (both £250 since there's a single line).
    expect(screen.getAllByText("£250")).toHaveLength(2);
    expect(screen.getByText("10 Feb 2026")).toBeInTheDocument();

    expect(screen.queryByRole("button", { name: /submit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit line" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
  });

  it("shows an empty state when the report has no lines", async () => {
    getReportMock.mockResolvedValue({ ...makeReport(), lines: [] });
    listReportLinesByReportMock.mockResolvedValue([]);

    renderDetail();

    await waitFor(() => expect(screen.getByText("No report lines yet.")).toBeInTheDocument());
  });

  it("shows the Report Summary total expenses and total amount across all lines", async () => {
    getReportMock.mockResolvedValue({ ...makeReport(), lines: [] });
    listReportLinesByReportMock.mockResolvedValue([
      makeLine({ id: "rl1", amount: 250 }),
      makeLine({ id: "rl2", amount: 300 }),
    ]);

    renderDetail();

    await waitFor(() => expect(screen.getByText("Report Summary")).toBeInTheDocument());
    expect(screen.getByText("Total Expenses")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByText("Total Amount")).toBeInTheDocument();
    expect(screen.getByText("£550")).toBeInTheDocument();
  });

  it("shows an error state when the report fails to load", async () => {
    getReportMock.mockRejectedValue(new Error("not found"));
    listReportLinesByReportMock.mockResolvedValue([]);

    renderDetail();

    await waitFor(() =>
      expect(screen.getByText("Failed to load this report.")).toBeInTheDocument(),
    );
  });
});

describe("ReportDetailView report line CRUD (draft only)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    fetchBudgetByIdMock.mockResolvedValue(makeBudget());
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    canReviewReportMock.mockReturnValue(false);
  });

  it("hides New Line and edit/delete controls once the report leaves draft", async () => {
    getReportMock.mockResolvedValue(makeReport({ status: "submitted" }));
    listReportLinesByReportMock.mockResolvedValue([makeLine()]);

    renderDetail();

    await waitFor(() => expect(screen.getByText("Fuel receipts")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "New Line" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit line" })).not.toBeInTheDocument();
  });

  it("adds a report line and appends it to the list", async () => {
    const user = userEvent.setup();
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    listReportLinesByReportMock.mockResolvedValue([]);
    createReportLineMock.mockResolvedValue(makeLine({ id: "new-line" }));

    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "New Line" })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "New Line" }));

    await user.selectOptions(screen.getByLabelText(/budget line/i), "bl1");
    await user.type(screen.getByLabelText(/^description/i), "Fuel receipts");
    const amountInput = screen.getByLabelText(/^amount/i);
    await user.clear(amountInput);
    await user.type(amountInput, "250");
    await user.type(screen.getByLabelText(/expense date/i), "2026-02-10");
    await user.click(screen.getByRole("button", { name: "Add Line" }));

    await waitFor(() =>
      expect(createReportLineMock).toHaveBeenCalledWith({
        report_id: "r1",
        budget_line_id: "bl1",
        description: "Fuel receipts",
        amount: 250,
        expense_date: "2026-02-10",
        extra_fields: {},
      }),
    );
    await waitFor(() => expect(screen.getByText("Fuel receipts")).toBeInTheDocument());
  });

  it("edits a line's description, amount, and expense date", async () => {
    const user = userEvent.setup();
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    listReportLinesByReportMock.mockResolvedValue([makeLine()]);
    updateReportLineMock.mockResolvedValue(
      makeLine({ description: "Updated receipts", amount: 300, expense_date: "2026-03-01" }),
    );

    renderDetail();

    await waitFor(() => expect(screen.getByText("Fuel receipts")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Edit line" }));
    const dateInput = screen.getByDisplayValue("2026-02-10");
    await user.clear(dateInput);
    await user.type(dateInput, "2026-03-01");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(updateReportLineMock).toHaveBeenCalledWith("rl1", {
        report_id: "r1",
        description: "Fuel receipts",
        amount: 250,
        expense_date: "2026-03-01",
      }),
    );
    await waitFor(() => expect(screen.getByText("Updated receipts")).toBeInTheDocument());
    await waitFor(() => expect(screen.getByText("01 Mar 2026")).toBeInTheDocument());
  });

  it("shows the backend's rejection message inline when an edit is rejected (e.g. expense_date outside the report period)", async () => {
    const user = userEvent.setup();
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    listReportLinesByReportMock.mockResolvedValue([makeLine()]);
    updateReportLineMock.mockRejectedValue({
      response: {
        data: {
          detail: "expense_date must fall within the report's period (2026-01-01 to 2026-03-31)",
        },
      },
    });

    renderDetail();

    await waitFor(() => expect(screen.getByText("Fuel receipts")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Edit line" }));
    const dateInput = screen.getByDisplayValue("2026-02-10");
    await user.clear(dateInput);
    await user.type(dateInput, "2026-07-29");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(
        screen.getByText(/expense_date must fall within the report's period/i),
      ).toBeInTheDocument(),
    );
    // Still in edit mode with the entered value intact, not silently reverted
    expect(screen.getByDisplayValue("2026-07-29")).toBeInTheDocument();
  });

  it("deletes a line and removes it from the list", async () => {
    const user = userEvent.setup();
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    listReportLinesByReportMock.mockResolvedValue([makeLine()]);
    deleteReportLineMock.mockResolvedValue({});

    renderDetail();

    await waitFor(() => expect(screen.getByText("Fuel receipts")).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "Delete line" }));
    await user.click(screen.getByRole("button", { name: "Yes" }));

    await waitFor(() => expect(deleteReportLineMock).toHaveBeenCalledWith("rl1"));
    await waitFor(() => expect(screen.queryByText("Fuel receipts")).not.toBeInTheDocument());
  });
});

describe("ReportDetailView extra fields", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    fetchBudgetByIdMock.mockResolvedValue(makeBudget());
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    canReviewReportMock.mockReturnValue(false);
  });

  it("shows a dynamic column for each extra_fields key already used on the report's lines", async () => {
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    listReportLinesByReportMock.mockResolvedValue([
      makeLine({ extra_fields: { receipt_no: "R-042" } }),
    ]);

    renderDetail();

    await waitFor(() => expect(screen.getByText("receipt_no")).toBeInTheDocument());
    expect(screen.getByText("R-042")).toBeInTheDocument();
  });

  it("prefills and locks existing extra field keys on the New Line form, and allows adding a new one", async () => {
    const user = userEvent.setup();
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    listReportLinesByReportMock.mockResolvedValue([
      makeLine({ extra_fields: { receipt_no: "R-042" } }),
    ]);
    createReportLineMock.mockResolvedValue(makeLine({ id: "new-line" }));

    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "New Line" })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "New Line" }));

    // Existing key is prefilled and its key input is locked (disabled)
    const keyInput = screen.getByDisplayValue("receipt_no");
    expect(keyInput).toBeDisabled();
    // No remove ("X") button for an existing/locked key
    expect(screen.queryByRole("button", { name: "X" })).not.toBeInTheDocument();

    await user.type(screen.getByPlaceholderText("Value"), "R-099");
    await user.click(screen.getByRole("button", { name: "+ Add Field" }));

    const keyInputs = screen.getAllByPlaceholderText("Key");
    await user.type(keyInputs[keyInputs.length - 1], "vendor");
    const valueInputs = screen.getAllByPlaceholderText("Value");
    await user.type(valueInputs[valueInputs.length - 1], "Acme Fuel Co");

    await user.selectOptions(screen.getByLabelText(/budget line/i), "bl1");
    await user.type(screen.getByLabelText(/^description/i), "Fuel receipts");
    const amountInput = screen.getByLabelText(/^amount/i);
    await user.clear(amountInput);
    await user.type(amountInput, "250");
    await user.type(screen.getByLabelText(/expense date/i), "2026-02-10");
    await user.click(screen.getByRole("button", { name: "Add Line" }));

    await waitFor(() =>
      expect(createReportLineMock).toHaveBeenCalledWith(
        expect.objectContaining({
          extra_fields: { receipt_no: "R-099", vendor: "Acme Fuel Co" },
        }),
      ),
    );
  });
});

describe("ReportDetailView submit transition", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    fetchBudgetByIdMock.mockResolvedValue(makeBudget());
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    canReviewReportMock.mockReturnValue(false);
    listReportLinesByReportMock.mockResolvedValue([]);
  });

  it("shows Submit only to the owner on a draft report", async () => {
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument(),
    );
  });

  it("hides Submit for a non-owner", async () => {
    isBudgetOwnerMock.mockReturnValue(false);
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    renderDetail();

    await waitFor(() => expect(screen.getByText("Q1 Report")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Submit" })).not.toBeInTheDocument();
  });

  it("submits the report and updates the displayed status", async () => {
    const user = userEvent.setup();
    getReportMock.mockResolvedValue(makeReport({ status: "draft" }));
    submitReportMock.mockResolvedValue(makeReport({ status: "submitted" }));

    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Submit" })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => expect(submitReportMock).toHaveBeenCalledWith("r1"));
    await waitFor(() => expect(screen.getByText("Submitted")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Submit" })).not.toBeInTheDocument();
  });
});

describe("ReportDetailView review actions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    fetchBudgetByIdMock.mockResolvedValue(makeBudget());
    listReportLinesByReportMock.mockResolvedValue([]);
  });

  it("shows Approve/Reject to an authorized reviewer on a submitted report", async () => {
    getCurrentCustomerIdMock.mockReturnValue("funder-1");
    isBudgetOwnerMock.mockReturnValue(false);
    canReviewReportMock.mockReturnValue(true);
    getReportMock.mockResolvedValue(makeReport({ status: "submitted" }));

    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument(),
    );
    expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument();
  });

  it("hides Approve/Reject from a non-reviewer", async () => {
    getCurrentCustomerIdMock.mockReturnValue("stranger-1");
    isBudgetOwnerMock.mockReturnValue(false);
    canReviewReportMock.mockReturnValue(false);
    getReportMock.mockResolvedValue(makeReport({ status: "submitted" }));

    renderDetail();

    await waitFor(() => expect(screen.getByText("Q1 Report")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("approves a submitted report with review notes", async () => {
    const user = userEvent.setup();
    getCurrentCustomerIdMock.mockReturnValue("funder-1");
    isBudgetOwnerMock.mockReturnValue(false);
    canReviewReportMock.mockReturnValue(true);
    getReportMock.mockResolvedValue(makeReport({ status: "submitted" }));
    reviewReportMock.mockResolvedValue(makeReport({ status: "approved" }));

    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Approve" })).toBeInTheDocument(),
    );
    await user.type(screen.getByLabelText(/review notes/i), "Looks good");
    await user.click(screen.getByRole("button", { name: "Approve" }));

    await waitFor(() =>
      expect(reviewReportMock).toHaveBeenCalledWith("r1", {
        decision: "approved",
        review_notes: "Looks good",
      }),
    );
    await waitFor(() => expect(screen.getByText("Approved")).toBeInTheDocument());
  });

  it("rejects a submitted report", async () => {
    const user = userEvent.setup();
    getCurrentCustomerIdMock.mockReturnValue("funder-1");
    isBudgetOwnerMock.mockReturnValue(false);
    canReviewReportMock.mockReturnValue(true);
    getReportMock.mockResolvedValue(makeReport({ status: "submitted" }));
    reviewReportMock.mockResolvedValue(makeReport({ status: "rejected" }));

    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Reject" })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Reject" }));

    await waitFor(() =>
      expect(reviewReportMock).toHaveBeenCalledWith("r1", {
        decision: "rejected",
        review_notes: undefined,
      }),
    );
    await waitFor(() => expect(screen.getByText("Rejected")).toBeInTheDocument());
  });
});

describe("ReportDetailView reopen transition", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listAttachmentsByReportLineMock.mockResolvedValue([]);
    fetchBudgetByIdMock.mockResolvedValue(makeBudget());
    listReportLinesByReportMock.mockResolvedValue([]);
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
    canReviewReportMock.mockReturnValue(false);
  });

  it("shows Reopen to the owner on a rejected report", async () => {
    getReportMock.mockResolvedValue(makeReport({ status: "rejected" }));
    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Reopen" })).toBeInTheDocument(),
    );
  });

  it("reopens the report, updates status, and re-enables line edits", async () => {
    const user = userEvent.setup();
    getReportMock.mockResolvedValue(makeReport({ status: "rejected" }));
    listReportLinesByReportMock.mockResolvedValue([makeLine()]);
    reopenReportMock.mockResolvedValue(makeReport({ status: "draft" }));

    renderDetail();

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Reopen" })).toBeInTheDocument(),
    );
    await user.click(screen.getByRole("button", { name: "Reopen" }));

    await waitFor(() => expect(reopenReportMock).toHaveBeenCalledWith("r1"));
    await waitFor(() => expect(screen.getByText("Draft")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Edit line" })).toBeInTheDocument();
  });
});
