import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi, type Mock } from "vitest";
import SettingsPage from "./Settings";
import * as aiSettingsApi from "@/api/aiSettingsApi";
import * as authContext from "@/context/AuthContext";
import * as donorGranteeApi from "@/api/donorGranteeApi";
import * as usersApi from "@/api/usersApi";
import * as customerApi from "@/api/customerApi";
import * as adminManagementApi from "@/api/adminManagementApi";

vi.mock("@/api/aiSettingsApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/aiSettingsApi")>();
  return {
    ...actual,
    getAiSettings: vi.fn(),
  };
});

// SecuritySection/PrivacySection fetch these unconditionally on mount —
// stub them so this test doesn't fire real network calls.
vi.mock("@/api/usersApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/usersApi")>();
  return {
    ...actual,
    listSessions: vi.fn(),
    getConsent: vi.fn(),
  };
});

vi.mock("@/context/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/context/AuthContext")>();
  return {
    ...actual,
    useAuth: vi.fn(),
  };
});

// ManageGrantees is only mounted for a donor — stub its data dependency so
// donor-path tests don't fire real network calls.
vi.mock("@/api/donorGranteeApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/donorGranteeApi")>();
  return {
    ...actual,
    listDonorGrantees: vi.fn(),
  };
});

// General/Team are admin-only — stub their data dependencies.
vi.mock("@/api/customerApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/customerApi")>();
  return {
    ...actual,
    getCustomer: vi.fn(),
  };
});

vi.mock("@/api/adminManagementApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/adminManagementApi")>();
  return {
    ...actual,
    listCompanyUsers: vi.fn(),
  };
});

const getAiSettingsMock = aiSettingsApi.getAiSettings as unknown as Mock;
const useAuthMock = authContext.useAuth as unknown as Mock;
const listDonorGranteesMock = donorGranteeApi.listDonorGrantees as unknown as Mock;
const listSessionsMock = usersApi.listSessions as unknown as Mock;
const getConsentMock = usersApi.getConsent as unknown as Mock;
const getCustomerMock = customerApi.getCustomer as unknown as Mock;
const listCompanyUsersMock = adminManagementApi.listCompanyUsers as unknown as Mock;

// getCurrentCustomerId reads the real JWT, not the mocked useAuth.
function makeFakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

function renderSettings() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <SettingsPage />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    sessionStorage.clear();
    getAiSettingsMock.mockResolvedValue({ providers: [] });
    listDonorGranteesMock.mockResolvedValue([]);
    listSessionsMock.mockResolvedValue([]);
    getConsentMock.mockResolvedValue({
      data_processing_granted: true,
      data_processing_at: "2026-01-01T00:00:00Z",
      marketing_granted: false,
      marketing_at: null,
    });
    getCustomerMock.mockResolvedValue({
      id: "cust-1",
      name: "Acme NGO",
      country: "GB",
      currency: "GBP",
      is_ngo: true,
      is_donor: false,
    });
    listCompanyUsersMock.mockResolvedValue([]);
  });

  it("does not show the Members & grantees nav item for a non-donor customer", async () => {
    useAuthMock.mockReturnValue({ isDonor: false, username: "user@example.com" });
    renderSettings();

    await waitFor(() => expect(screen.getByText("Account Settings")).toBeInTheDocument());
    expect(screen.queryByText("Members & grantees")).not.toBeInTheDocument();
    expect(listDonorGranteesMock).not.toHaveBeenCalled();
  });

  it("shows Manage Grantees after selecting Members & grantees for a donor customer", async () => {
    useAuthMock.mockReturnValue({ isDonor: true, username: "user@example.com" });
    renderSettings();
    const user = userEvent.setup();

    await user.click(await screen.findByText("Members & grantees"));

    await waitFor(() => expect(screen.getByText("Manage Grantees")).toBeInTheDocument());
  });

  it("defaults to the Profile section", async () => {
    useAuthMock.mockReturnValue({ isDonor: false, username: "user@example.com" });
    renderSettings();

    await waitFor(() =>
      expect(screen.getByRole("heading", { name: "Profile" })).toBeInTheDocument(),
    );
    expect(screen.getByDisplayValue("user@example.com")).toBeInTheDocument();
  });

  it("does not show General/Team nav items for a plain user", async () => {
    useAuthMock.mockReturnValue({ isDonor: false, username: "user@example.com" });
    renderSettings();

    await waitFor(() => expect(screen.getByText("Account Settings")).toBeInTheDocument());
    expect(screen.queryByText("General")).not.toBeInTheDocument();
    expect(screen.queryByText("Team")).not.toBeInTheDocument();
  });

  it("shows the company picker after selecting General for a superuser who isn't impersonating", async () => {
    useAuthMock.mockReturnValue({
      isDonor: false,
      isSuperuser: true,
      username: "super@example.com",
    });
    renderSettings();
    const user = userEvent.setup();

    await user.click(await screen.findByText("General"));

    expect(await screen.findByText("Manage a company")).toBeInTheDocument();
    expect(screen.queryByText("Team")).not.toBeInTheDocument();
  });

  it("shows company details and team members for a real company admin", async () => {
    localStorage.setItem("token", makeFakeJwt({ role: "admin", customer_id: "cust-1" }));
    useAuthMock.mockReturnValue({
      isDonor: false,
      isAdmin: true,
      username: "admin@example.com",
    });
    renderSettings();
    const user = userEvent.setup();

    await user.click(await screen.findByText("General"));
    expect(await screen.findByText("Company details")).toBeInTheDocument();
    expect(screen.queryByText("Danger zone")).not.toBeInTheDocument();

    await user.click(screen.getByText("Team"));
    expect(await screen.findByText("Team members")).toBeInTheDocument();
  });

  it("also shows the danger zone for a superuser mid-impersonation", async () => {
    localStorage.setItem(
      "token",
      makeFakeJwt({ role: "admin", customer_id: "cust-1", is_impersonating: true }),
    );
    useAuthMock.mockReturnValue({
      isDonor: false,
      isAdmin: true,
      isSuperuser: true,
      isImpersonating: true,
      username: "super@example.com",
    });
    renderSettings();
    const user = userEvent.setup();

    await user.click(await screen.findByText("General"));

    expect(await screen.findByText("Company details")).toBeInTheDocument();
    expect(screen.getByText("Danger zone")).toBeInTheDocument();
  });
});
