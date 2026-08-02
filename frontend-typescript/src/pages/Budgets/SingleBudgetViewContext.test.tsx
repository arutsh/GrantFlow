import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import {
  SingleBudgetViewContextProvider,
  useDetailedBudget,
} from "./SingleBudgetViewContext";
import { Budget, Report, ReportLine } from "./types/budget";
import * as gatewayApi from "@/api/gatewayApi";
import * as reportApi from "@/api/reportApi";

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
    listReportsByBudget: vi.fn(),
    listReportLinesByReport: vi.fn(),
  };
});

const fetchBudgetByIdMock = gatewayApi.fetchBudgetById as unknown as Mock;
const listReportsByBudgetMock = reportApi.listReportsByBudget as unknown as Mock;
const listReportLinesByReportMock = reportApi.listReportLinesByReport as unknown as Mock;

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

function makeReport(overrides: Partial<Report> = {}): Report {
  return { id: "r1", budget_id: "b1", name: "Report 1", status: "draft", ...overrides };
}

function makeLine(overrides: Partial<ReportLine> = {}): ReportLine {
  return { id: "rl1", report_id: "r1", budget_line_id: "bl1", amount: 100, ...overrides };
}

function Consumer() {
  const { spendByLineId, totalReported, hasReports } = useDetailedBudget();
  return (
    <div>
      <span data-testid="total">{totalReported}</span>
      <span data-testid="bl1">{spendByLineId["bl1"] ?? 0}</span>
      <span data-testid="bl2">{spendByLineId["bl2"] ?? 0}</span>
      <span data-testid="hasReports">{String(hasReports)}</span>
    </div>
  );
}

function renderContext() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SingleBudgetViewContextProvider id="b1">
        <Consumer />
      </SingleBudgetViewContextProvider>
    </QueryClientProvider>,
  );
}

describe("SingleBudgetViewContext spend aggregation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchBudgetByIdMock.mockResolvedValue(makeBudget());
  });

  it("sums reported spend per budget line across every report on the budget", async () => {
    listReportsByBudgetMock.mockResolvedValue([
      makeReport({ id: "r1", status: "submitted" }),
      makeReport({ id: "r2", status: "submitted" }),
    ]);
    listReportLinesByReportMock.mockImplementation((reportId: string) =>
      Promise.resolve(
        reportId === "r1"
          ? [makeLine({ id: "rl1", report_id: "r1", budget_line_id: "bl1", amount: 100 })]
          : [makeLine({ id: "rl2", report_id: "r2", budget_line_id: "bl1", amount: 400 })],
      ),
    );

    renderContext();

    await waitFor(() => expect(screen.getByTestId("bl1")).toHaveTextContent("500"));
    expect(screen.getByTestId("bl2")).toHaveTextContent("0");
    expect(screen.getByTestId("total")).toHaveTextContent("500");
    expect(screen.getByTestId("hasReports")).toHaveTextContent("true");
  });

  it("reports zero spend when the budget has no reports yet", async () => {
    listReportsByBudgetMock.mockResolvedValue([]);

    renderContext();

    await waitFor(() => expect(listReportsByBudgetMock).toHaveBeenCalledWith("b1"));
    expect(screen.getByTestId("total")).toHaveTextContent("0");
    expect(listReportLinesByReportMock).not.toHaveBeenCalled();
    expect(screen.getByTestId("hasReports")).toHaveTextContent("false");
  });

  it("does not count a draft-only report — nothing has actually been reported yet", async () => {
    listReportsByBudgetMock.mockResolvedValue([makeReport({ id: "r1", status: "draft" })]);
    listReportLinesByReportMock.mockResolvedValue([]);

    renderContext();

    await waitFor(() => expect(listReportsByBudgetMock).toHaveBeenCalledWith("b1"));
    expect(screen.getByTestId("hasReports")).toHaveTextContent("false");
  });
});
