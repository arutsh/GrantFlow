import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { ManageGrantees } from "./ManageGrantees";
import * as donorGranteeApi from "@/api/donorGranteeApi";
import * as customerApi from "@/api/customerApi";

vi.mock("@/api/donorGranteeApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/donorGranteeApi")>();
  return {
    ...actual,
    listDonorGrantees: vi.fn(),
    createDonorGrantee: vi.fn(),
    deleteDonorGrantee: vi.fn(),
  };
});

vi.mock("@/api/customerApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/customerApi")>();
  return {
    ...actual,
    searchCustomers: vi.fn(),
    getCustomersByIds: vi.fn(),
  };
});

const listDonorGranteesMock = donorGranteeApi.listDonorGrantees as unknown as Mock;
const createDonorGranteeMock = donorGranteeApi.createDonorGrantee as unknown as Mock;
const deleteDonorGranteeMock = donorGranteeApi.deleteDonorGrantee as unknown as Mock;
const searchCustomersMock = customerApi.searchCustomers as unknown as Mock;
const getCustomersByIdsMock = customerApi.getCustomersByIds as unknown as Mock;

function renderComponent() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ManageGrantees />
    </QueryClientProvider>,
  );
}

describe("ManageGrantees", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows an empty state when the donor has zero approved grantees", async () => {
    listDonorGranteesMock.mockResolvedValue([]);
    renderComponent();

    await waitFor(() => expect(screen.getByText("No approved grantees yet")).toBeInTheDocument());
    expect(getCustomersByIdsMock).not.toHaveBeenCalled();
  });

  it("renders the approved grantee list resolved to customer names", async () => {
    listDonorGranteesMock.mockResolvedValue([
      { id: "dg1", donor_id: "donor-1", grantee_id: "g1" },
      { id: "dg2", donor_id: "donor-1", grantee_id: "g2" },
    ]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "g1", name: "Hope Relief NGO", country: "GB", is_ngo: true, is_donor: false, currency: "GBP" },
      { id: "g2", name: "Clean Water Trust", country: "KE", is_ngo: true, is_donor: false, currency: "KES" },
    ]);
    renderComponent();

    await waitFor(() => expect(screen.getByText("Hope Relief NGO")).toBeInTheDocument());
    expect(screen.getByText("Clean Water Trust")).toBeInTheDocument();
    expect(getCustomersByIdsMock).toHaveBeenCalledWith(["g1", "g2"]);
  });

  it("searches for NGOs and excludes already-approved grantees from results", async () => {
    const user = userEvent.setup();
    listDonorGranteesMock.mockResolvedValue([
      { id: "dg1", donor_id: "donor-1", grantee_id: "g1" },
    ]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "g1", name: "Hope Relief NGO", country: "GB", is_ngo: true, is_donor: false, currency: "GBP" },
    ]);
    searchCustomersMock.mockResolvedValue([
      { id: "g1", name: "Hope Relief NGO", country: "GB", is_ngo: true, is_donor: false, currency: "GBP" },
      { id: "g3", name: "New Hope Org", country: "US", is_ngo: true, is_donor: false, currency: "USD" },
    ]);
    renderComponent();

    await waitFor(() => expect(screen.getByText("Hope Relief NGO")).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText("Search NGOs by name"), "Hope");
    await user.click(screen.getByRole("button", { name: "Search" }));

    await waitFor(() =>
      expect(searchCustomersMock).toHaveBeenCalledWith({ is_ngo: true, search: "Hope" }),
    );
    await waitFor(() => expect(screen.getByText("New Hope Org")).toBeInTheDocument());
    // g1 is already approved, so it must not show up as an addable search result.
    expect(screen.getAllByText("Hope Relief NGO").length).toBe(1);
  });

  it("adds a grantee from search results and reflects it in the approved list without reload", async () => {
    const user = userEvent.setup();
    listDonorGranteesMock
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ id: "dg1", donor_id: "donor-1", grantee_id: "g3" }]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "g3", name: "New Hope Org", country: "US", is_ngo: true, is_donor: false, currency: "USD" },
    ]);
    searchCustomersMock.mockResolvedValue([
      { id: "g3", name: "New Hope Org", country: "US", is_ngo: true, is_donor: false, currency: "USD" },
    ]);
    createDonorGranteeMock.mockResolvedValue({ id: "dg1", donor_id: "donor-1", grantee_id: "g3" });

    renderComponent();
    await waitFor(() => expect(screen.getByText("No approved grantees yet")).toBeInTheDocument());

    await user.type(screen.getByPlaceholderText("Search NGOs by name"), "New Hope");
    await user.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(screen.getByText("New Hope Org")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Add" }));

    await waitFor(() => expect(createDonorGranteeMock).toHaveBeenCalledWith("g3"));
    await waitFor(() => expect(listDonorGranteesMock).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(screen.queryByText("No approved grantees yet")).not.toBeInTheDocument(),
    );
  });

  it("revokes an approved grantee and it disappears from the list without reload", async () => {
    const user = userEvent.setup();
    listDonorGranteesMock
      .mockResolvedValueOnce([{ id: "dg1", donor_id: "donor-1", grantee_id: "g1" }])
      .mockResolvedValueOnce([]);
    getCustomersByIdsMock.mockResolvedValue([
      { id: "g1", name: "Hope Relief NGO", country: "GB", is_ngo: true, is_donor: false, currency: "GBP" },
    ]);
    deleteDonorGranteeMock.mockResolvedValue(undefined);

    renderComponent();
    await waitFor(() => expect(screen.getByText("Hope Relief NGO")).toBeInTheDocument());

    await user.click(screen.getByRole("button", { name: "Revoke" }));

    await waitFor(() => expect(deleteDonorGranteeMock).toHaveBeenCalledWith("dg1"));
    await waitFor(() => expect(screen.getByText("No approved grantees yet")).toBeInTheDocument());
  });
});
