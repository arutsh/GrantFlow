import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { ImpersonatePicker } from "./ImpersonatePicker";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import * as customerApi from "@/api/customerApi";
import * as authApi from "@/api/authApi";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function makeFakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

function TestExitProbe() {
  const { isImpersonating, impersonatedCustomerName } = useAuth();
  return (
    <div data-testid="impersonation-state">
      {String(isImpersonating)}:{impersonatedCustomerName ?? ""}
    </div>
  );
}

function renderPicker() {
  localStorage.setItem("token", makeFakeJwt({ role: "superuser" }));
  localStorage.setItem("username", "Root Admin");
  const queryClient = new QueryClient();
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ImpersonatePicker />
          <TestExitProbe />
        </AuthProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("ImpersonatePicker", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    mockNavigate.mockClear();
  });

  it("searches customers as the user types and starts impersonation on selection", async () => {
    const user = userEvent.setup();
    vi.spyOn(customerApi, "searchCustomers").mockResolvedValue([
      { id: "cust-1", name: "Acme NGO", country: "US", is_ngo: true, is_donor: false, currency: "USD" },
    ]);
    vi.spyOn(authApi, "impersonateCustomer").mockResolvedValue({
      access_token: makeFakeJwt({ role: "admin", is_impersonating: true, customer_id: "cust-1" }),
      token_type: "bearer",
      customer_id: "cust-1",
      customer_name: "Acme NGO",
      expires_in: 900,
    });

    renderPicker();

    await user.click(screen.getByRole("button", { name: "Impersonate a customer" }));
    await user.type(screen.getByPlaceholderText("Search customers by name"), "Acme");

    const result = await screen.findByText("Acme NGO");
    await user.click(result);

    await waitFor(() => {
      expect(screen.getByTestId("impersonation-state")).toHaveTextContent("true:Acme NGO");
    });
    expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
  });

  it("shows an error if starting impersonation fails", async () => {
    const user = userEvent.setup();
    vi.spyOn(customerApi, "searchCustomers").mockResolvedValue([
      { id: "cust-1", name: "Acme NGO", country: "US", is_ngo: true, is_donor: false, currency: "USD" },
    ]);
    vi.spyOn(authApi, "impersonateCustomer").mockRejectedValue(new Error("forbidden"));

    renderPicker();

    await user.click(screen.getByRole("button", { name: "Impersonate a customer" }));
    await user.type(screen.getByPlaceholderText("Search customers by name"), "Acme");

    const result = await screen.findByText("Acme NGO");
    await user.click(result);

    expect(await screen.findByText("Failed to start impersonation.")).toBeInTheDocument();
  });
});
