import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { ReportsList } from "./ReportsList";
import { Budget, Report } from "../types/budget";
import * as reportApi from "@/api/reportApi";
import * as roleAccess from "@/utils/roleAccess";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

vi.mock("@/api/reportApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/reportApi")>();
  return {
    ...actual,
    listReportsByBudget: vi.fn(),
    createReport: vi.fn(),
  };
});

vi.mock("@/utils/roleAccess", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/utils/roleAccess")>();
  return {
    ...actual,
    getCurrentCustomerId: vi.fn(),
    isBudgetOwner: vi.fn(),
  };
});

const listReportsByBudgetMock = reportApi.listReportsByBudget as unknown as Mock;
const createReportMock = reportApi.createReport as unknown as Mock;
const getCurrentCustomerIdMock = roleAccess.getCurrentCustomerId as unknown as Mock;
const isBudgetOwnerMock = roleAccess.isBudgetOwner as unknown as Mock;

function makeBudget(overrides: Partial<Budget> = {}): Budget {
  return {
    id: "b1",
    name: "Clean Water Phase 1",
    status: "confirmed",
    owner: { id: "owner-1", name: "Hope Relief NGO" },
    ...overrides,
  };
}

function makeReport(overrides: Partial<Report> = {}): Report {
  return {
    id: "r1",
    budget_id: "b1",
    name: "Q1 Report",
    status: "draft",
    period_start: "2026-01-01",
    period_end: "2026-03-31",
    ...overrides,
  };
}

function renderList(budget: Budget) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ReportsList budget={budget} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ReportsList", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getCurrentCustomerIdMock.mockReturnValue("owner-1");
    isBudgetOwnerMock.mockReturnValue(true);
  });

  it("is hidden on a non-confirmed budget with no reports", async () => {
    listReportsByBudgetMock.mockResolvedValue([]);
    renderList(makeBudget({ status: "draft" }));

    await waitFor(() => expect(listReportsByBudgetMock).toHaveBeenCalled());
    expect(screen.queryByText("Reports")).not.toBeInTheDocument();
  });

  it("shows historical reports on a non-confirmed (e.g. archived) budget", async () => {
    listReportsByBudgetMock.mockResolvedValue([makeReport()]);
    renderList(makeBudget({ status: "archived" }));

    await waitFor(() => expect(screen.getByText("Q1 Report")).toBeInTheDocument());
  });

  it("shows an empty state with a New Report action on a confirmed budget with no reports", async () => {
    listReportsByBudgetMock.mockResolvedValue([]);
    renderList(makeBudget());

    await waitFor(() => expect(screen.getByText("No reports yet.")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "New Report" })).toBeInTheDocument();
  });

  it("hides the New Report action for a non-owner", async () => {
    isBudgetOwnerMock.mockReturnValue(false);
    listReportsByBudgetMock.mockResolvedValue([]);
    renderList(makeBudget());

    await waitFor(() => expect(screen.getByText("No reports yet.")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: "New Report" })).not.toBeInTheDocument();
  });

  it("lists each report's name, period, and status", async () => {
    listReportsByBudgetMock.mockResolvedValue([
      makeReport({ id: "r1", name: "Q1 Report", status: "draft" }),
      makeReport({ id: "r2", name: "Q2 Report", status: "submitted" }),
    ]);
    renderList(makeBudget());

    await waitFor(() => expect(screen.getByText("Q1 Report")).toBeInTheDocument());
    expect(screen.getByText("Q2 Report")).toBeInTheDocument();
    expect(screen.getByText("Draft")).toBeInTheDocument();
    expect(screen.getByText("Submitted")).toBeInTheDocument();
  });

  it("navigates to a report's detail route on click", async () => {
    const user = userEvent.setup();
    listReportsByBudgetMock.mockResolvedValue([makeReport()]);
    renderList(makeBudget());

    await waitFor(() => expect(screen.getByText("Q1 Report")).toBeInTheDocument());
    await user.click(screen.getByText("Q1 Report"));

    expect(mockNavigate).toHaveBeenCalledWith("/budgets/b1/reports/r1");
  });

  it("creates a report with the default period and navigates to its detail view", async () => {
    const user = userEvent.setup();
    listReportsByBudgetMock.mockResolvedValue([]);
    createReportMock.mockResolvedValue(makeReport({ id: "new-r" }));
    renderList(makeBudget());

    await waitFor(() => expect(screen.getByRole("button", { name: "New Report" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "New Report" }));

    await user.type(screen.getByLabelText(/^name/i), "Q1 Report");
    await user.click(screen.getByRole("button", { name: "Create Report" }));

    await waitFor(() =>
      expect(createReportMock).toHaveBeenCalledWith({
        budget_id: "b1",
        name: "Q1 Report",
        period_start: undefined,
        period_end: undefined,
      }),
    );
    await waitFor(() =>
      expect(mockNavigate).toHaveBeenCalledWith("/budgets/b1/reports/new-r"),
    );
  });

  it("shows the backend's rejection message inline and keeps the form open on an overlapping period", async () => {
    const user = userEvent.setup();
    listReportsByBudgetMock.mockResolvedValue([]);
    createReportMock.mockRejectedValue({
      response: { data: { detail: "Report period overlaps an existing report" } },
    });
    renderList(makeBudget());

    await waitFor(() => expect(screen.getByRole("button", { name: "New Report" })).toBeInTheDocument());
    await user.click(screen.getByRole("button", { name: "New Report" }));
    await user.type(screen.getByLabelText(/^name/i), "Q1 Report");
    await user.click(screen.getByRole("button", { name: "Create Report" }));

    await waitFor(() =>
      expect(screen.getByText("Report period overlaps an existing report")).toBeInTheDocument(),
    );
    expect(mockNavigate).not.toHaveBeenCalled();
    // Form stays open with the entered value intact
    expect(screen.getByDisplayValue("Q1 Report")).toBeInTheDocument();
  });
});
