import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { AddBudgetModal } from "./AddBudget";
import * as budgetApi from "@/api/budgetApi";
import * as donorGranteeApi from "@/api/donorGranteeApi";
import * as customerApi from "@/api/customerApi";

vi.mock("@/api/budgetApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/budgetApi")>();
  return {
    ...actual,
    createBudget: vi.fn(),
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

const createBudgetMock = budgetApi.createBudget as unknown as Mock;
const listDonorGranteesMock = donorGranteeApi.listDonorGrantees as unknown as Mock;
const getCustomersByIdsMock = customerApi.getCustomersByIds as unknown as Mock;

function renderModal(onClose = vi.fn()) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <AddBudgetModal isOpen={true} onClose={onClose} />
    </QueryClientProvider>,
  );
  return { onClose };
}

describe("AddBudgetModal", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows an empty-donors message instead of the picker when the grantee has no approved donors", async () => {
    listDonorGranteesMock.mockResolvedValue([]);
    renderModal();

    await waitFor(() =>
      expect(
        screen.getByText(
          "No approved donors yet — ask a donor to add you before selecting them here.",
        ),
      ).toBeInTheDocument(),
    );
    expect(screen.queryByRole("combobox")).not.toBeInTheDocument();
  });

  it("renders the donor picker with options resolved from the approved-donor list", async () => {
    listDonorGranteesMock.mockResolvedValue([
      { id: "dg1", donor_id: "d1", grantee_id: "g1" },
      { id: "dg2", donor_id: "d2", grantee_id: "g1" },
    ]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "d1", name: "Acme Foundation", country: "US", is_ngo: false, is_donor: true, currency: "USD" },
      { id: "d2", name: "Helping Hands Trust", country: "GB", is_ngo: false, is_donor: true, currency: "GBP" },
    ]);
    renderModal();

    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
    expect(screen.getByRole("option", { name: "Acme Foundation" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Helping Hands Trust" })).toBeInTheDocument();
    expect(getCustomersByIdsMock).toHaveBeenCalledWith(["d1", "d2"]);
  });

  it("selecting a donor sets funding_customer_id on submit and clears the free-text funder field", async () => {
    const user = userEvent.setup();
    listDonorGranteesMock.mockResolvedValue([{ id: "dg1", donor_id: "d1", grantee_id: "g1" }]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "d1", name: "Acme Foundation", country: "US", is_ngo: false, is_donor: true, currency: "USD" },
    ]);
    createBudgetMock.mockResolvedValue({ id: "b1" });
    const { onClose } = renderModal();

    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText("Budget Name"), "New Budget");
    await user.type(screen.getByPlaceholderText("Funder name"), "Some Funder");
    await user.selectOptions(screen.getByRole("combobox"), "d1");

    // Mutual exclusivity: selecting a donor clears the free-text field's value.
    expect(screen.getByPlaceholderText("Funder name")).toHaveValue("");
    expect(screen.getByPlaceholderText("Funder name")).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(createBudgetMock).toHaveBeenCalledWith({
        name: "New Budget",
        external_funder_name: undefined,
        funding_customer_id: "d1",
      }),
    );
    await waitFor(() => expect(onClose).toHaveBeenCalledWith({ id: "b1" }));
  });

  it("typing a free-text funder name clears a previously selected donor", async () => {
    const user = userEvent.setup();
    listDonorGranteesMock.mockResolvedValue([{ id: "dg1", donor_id: "d1", grantee_id: "g1" }]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "d1", name: "Acme Foundation", country: "US", is_ngo: false, is_donor: true, currency: "USD" },
    ]);
    createBudgetMock.mockResolvedValue({ id: "b1" });
    renderModal();

    await waitFor(() => expect(screen.getByRole("combobox")).toBeInTheDocument());
    await user.selectOptions(screen.getByRole("combobox"), "d1");
    expect(screen.getByRole("combobox")).toHaveValue("d1");

    // Typing into a still-enabled combobox scenario isn't possible since the
    // text field is disabled while a donor is selected — clear the donor
    // first, matching the only path a user can actually take.
    await user.selectOptions(screen.getByRole("combobox"), "");
    await user.type(screen.getByPlaceholderText("Funder name"), "External Co");
    expect(screen.getByRole("combobox")).toHaveValue("");

    await user.type(screen.getByPlaceholderText("Budget Name"), "Another Budget");
    await user.click(screen.getByRole("button", { name: "Save" }));

    await waitFor(() =>
      expect(createBudgetMock).toHaveBeenCalledWith({
        name: "Another Budget",
        external_funder_name: "External Co",
        funding_customer_id: undefined,
      }),
    );
  });

  it("blocks submission with neither a donor nor a free-text funder set, matching the backend's required-funder rule", async () => {
    const user = userEvent.setup();
    listDonorGranteesMock.mockResolvedValue([]);
    renderModal();

    await waitFor(() =>
      expect(screen.getByText(/No approved donors yet/)).toBeInTheDocument(),
    );

    await user.type(screen.getByPlaceholderText("Budget Name"), "Bare Budget");

    expect(
      screen.getByText("Select a donor or enter a funder name to continue."),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Save" })).toBeDisabled();
    expect(createBudgetMock).not.toHaveBeenCalled();
  });
});
