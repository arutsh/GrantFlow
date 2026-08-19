import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { ImportExcelModal } from "./ImportExcelModal";
import * as budgetApi from "@/api/budgetApi";

vi.mock("@/api/budgetApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/budgetApi")>();
  return {
    ...actual,
    importBudgetFromExcel: vi.fn(),
  };
});

const importBudgetFromExcelMock = budgetApi.importBudgetFromExcel as unknown as Mock;

function renderModal(onClose = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ImportExcelModal isOpen onClose={onClose} />
    </QueryClientProvider>,
  );
  return onClose;
}

describe("ImportExcelModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("rejects a non-.xlsx file client-side without calling the import endpoint", async () => {
    const user = userEvent.setup({ applyAccept: false });
    renderModal();

    const badFile = new File(["hello"], "notes.csv", { type: "text/csv" });
    await user.upload(screen.getByLabelText("Import budget from Excel"), badFile);

    expect(screen.getByText(/only \.xlsx files are supported/i)).toBeInTheDocument();
    expect(importBudgetFromExcelMock).not.toHaveBeenCalled();
  });

  it("rejects an oversized file client-side without calling the import endpoint", async () => {
    const user = userEvent.setup();
    renderModal();

    const oversized = new File([new Uint8Array(11 * 1024 * 1024)], "big.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    await user.upload(screen.getByLabelText("Import budget from Excel"), oversized);

    expect(screen.getByText(/exceeds the 10mb limit/i)).toBeInTheDocument();
    expect(importBudgetFromExcelMock).not.toHaveBeenCalled();
  });

  it("uploads a valid file and closes with the created budget", async () => {
    const onClose = renderModal();
    const createdBudget = { id: "b1", name: "Imported budget", status: "ai_draft" };
    importBudgetFromExcelMock.mockResolvedValue(createdBudget);
    const user = userEvent.setup();

    const file = new File(["fake"], "budget.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    await user.upload(screen.getByLabelText("Import budget from Excel"), file);

    await waitFor(() => expect(importBudgetFromExcelMock).toHaveBeenCalled());
    expect(importBudgetFromExcelMock.mock.calls[0][0]).toBeInstanceOf(File);
    await waitFor(() => expect(onClose).toHaveBeenCalledWith(createdBudget));
  });

  it("shows the backend's rejection message and does not close the modal", async () => {
    const onClose = renderModal();
    importBudgetFromExcelMock.mockRejectedValue({
      response: { data: { detail: "Only .xlsx files are supported" } },
    });
    const user = userEvent.setup();

    const file = new File(["fake"], "budget.xlsx", {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    });
    await user.upload(screen.getByLabelText("Import budget from Excel"), file);

    await waitFor(() =>
      expect(screen.getByText("Only .xlsx files are supported")).toBeInTheDocument(),
    );
    expect(onClose).not.toHaveBeenCalled();
  });

  it("calls onClose(null) on Cancel", async () => {
    const onClose = renderModal();
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "Cancel" }));

    expect(onClose).toHaveBeenCalledWith(null);
  });
});
