import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { ImpersonationBanner } from "./ImpersonationBanner";
import { AuthProvider, useAuth } from "@/context/AuthContext";

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

// Drives startImpersonation from within the provider tree, the same way
// ImpersonatePicker would after a successful /auth/impersonate call.
function ImpersonationTrigger() {
  const { startImpersonation } = useAuth();
  return (
    <button
      onClick={() =>
        startImpersonation(
          makeFakeJwt({ role: "admin", is_impersonating: true, customer_id: "cust-1" }),
          "Acme NGO",
        )
      }
    >
      TriggerImpersonation
    </button>
  );
}

function renderBanner() {
  localStorage.setItem("token", makeFakeJwt({ role: "superuser" }));
  localStorage.setItem("username", "Root Admin");
  const queryClient = new QueryClient();
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <ImpersonationTrigger />
          <ImpersonationBanner />
        </AuthProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("ImpersonationBanner", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    mockNavigate.mockClear();
  });

  it("renders nothing when there is no active impersonation session", () => {
    renderBanner();
    expect(screen.queryByText(/Impersonating/)).not.toBeInTheDocument();
  });

  it("appears immediately, naming the customer, once impersonation starts", async () => {
    const user = userEvent.setup();
    renderBanner();

    await user.click(screen.getByText("TriggerImpersonation"));

    expect(await screen.findByText(/Acme NGO/)).toBeInTheDocument();
  });

  it("offers no control besides Exit — nothing to dismiss or hide the banner", async () => {
    const user = userEvent.setup();
    renderBanner();
    await user.click(screen.getByText("TriggerImpersonation"));
    await screen.findByText(/Acme NGO/);

    expect(screen.getAllByRole("button")).toHaveLength(2); // TriggerImpersonation + Exit
    expect(screen.getByRole("button", { name: "Exit impersonation" })).toBeInTheDocument();
  });

  it("exit restores the superuser's own session and removes the banner", async () => {
    const user = userEvent.setup();
    renderBanner();
    await user.click(screen.getByText("TriggerImpersonation"));
    await screen.findByText(/Acme NGO/);

    await user.click(screen.getByRole("button", { name: "Exit impersonation" }));

    await waitFor(() => {
      expect(screen.queryByText(/Acme NGO/)).not.toBeInTheDocument();
    });
    expect(mockNavigate).toHaveBeenCalledWith("/dashboard");
  });
});
