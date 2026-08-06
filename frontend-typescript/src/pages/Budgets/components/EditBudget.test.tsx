import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { EditBudgetModal } from "./EditBudget";
import { Budget } from "../types/budget";
import * as budgetApi from "@/api/budgetApi";
import * as donorGranteeApi from "@/api/donorGranteeApi";
import * as customerApi from "@/api/customerApi";

vi.mock("@/api/budgetApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/budgetApi")>();
  return {
    ...actual,
    editBudget: vi.fn(),
  };
});

vi.mock("@/api/donorGranteeApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/donorGranteeApi")>();
  return {
    ...actual,
    listDonorGrantees: vi.fn(),
  };
});

vi.mock("@/api/customerApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/customerApi")>();
  return {
    ...actual,
    getCustomersByIds: vi.fn(),
  };
});

const editBudgetMock = budgetApi.editBudget as unknown as Mock;
const listDonorGranteesMock = donorGranteeApi.listDonorGrantees as unknown as Mock;
const getCustomersByIdsMock = customerApi.getCustomersByIds as unknown as Mock;

function makeBudget(overrides: Partial<Budget> = {}): Budget {
  return {
    id: "b1",
    name: "Clean Water Phase 1",
    status: "draft",
    owner: { id: "owner-1", name: "Hope Relief NGO" },
    funder: { id: "funder-1", name: "Donor 7" },
    ...overrides,
  };
}

function renderModal(data: Budget, onClose = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <EditBudgetModal isOpen={true} onClose={onClose} data={data} />
    </QueryClientProvider>,
  );
  return { onClose };
}

describe("EditBudgetModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    listDonorGranteesMock.mockResolvedValue([]);
  });

  it("preselects the donor option for a donor-linked funder, with the free-text field cleared and disabled", async () => {
    listDonorGranteesMock.mockResolvedValue([
      { id: "dg1", donor_id: "funder-1", grantee_id: "owner-1" },
    ]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "funder-1", name: "Donor 7", country: "GB", is_ngo: false, is_donor: true, currency: "GBP" },
    ]);

    renderModal(makeBudget());

    await waitFor(() => expect(screen.getByRole("combobox", { name: "Donor" })).toHaveValue("funder-1"));
    expect(screen.getByPlaceholderText("Funder name")).toHaveValue("");
    expect(screen.getByPlaceholderText("Funder name")).toBeDisabled();
  });

  it("prefills the free-text field for a custom-named funder", async () => {
    renderModal(makeBudget({ funder: { name: "External Co" } }));

    await waitFor(() => expect(screen.getByPlaceholderText("Funder name")).toHaveValue("External Co"));
  });

  it("saving without touching the funder preserves funding_customer_id instead of duplicating the donor name into external_funder_name", async () => {
    const user = userEvent.setup();
    listDonorGranteesMock.mockResolvedValue([
      { id: "dg1", donor_id: "funder-1", grantee_id: "owner-1" },
    ]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "funder-1", name: "Donor 7", country: "GB", is_ngo: false, is_donor: true, currency: "GBP" },
    ]);
    editBudgetMock.mockResolvedValue(makeBudget({ name: "Renamed" }));

    renderModal(makeBudget());
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Donor" })).toHaveValue("funder-1"));

    await user.clear(screen.getByPlaceholderText("Budget Name"));
    await user.type(screen.getByPlaceholderText("Budget Name"), "Renamed");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(editBudgetMock).toHaveBeenCalledWith("b1", {
        name: "Renamed",
        external_funder_name: "",
        funding_customer_id: "funder-1",
      }),
    );
  });

  it("switching to a custom name clears funding_customer_id via explicit null", async () => {
    const user = userEvent.setup();
    listDonorGranteesMock.mockResolvedValue([
      { id: "dg1", donor_id: "funder-1", grantee_id: "owner-1" },
    ]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "funder-1", name: "Donor 7", country: "GB", is_ngo: false, is_donor: true, currency: "GBP" },
    ]);
    editBudgetMock.mockResolvedValue(makeBudget({ funder: { name: "Custom Co" } }));

    renderModal(makeBudget());
    await waitFor(() => expect(screen.getByRole("combobox", { name: "Donor" })).toHaveValue("funder-1"));

    await user.selectOptions(screen.getByRole("combobox", { name: "Donor" }), "");
    await user.type(screen.getByPlaceholderText("Funder name"), "Custom Co");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(editBudgetMock).toHaveBeenCalledWith("b1", {
        name: "Clean Water Phase 1",
        external_funder_name: "Custom Co",
        funding_customer_id: null,
      }),
    );
  });
});
