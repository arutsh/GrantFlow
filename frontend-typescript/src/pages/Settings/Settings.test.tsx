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

const getAiSettingsMock = aiSettingsApi.getAiSettings as unknown as Mock;
const useAuthMock = authContext.useAuth as unknown as Mock;
const listDonorGranteesMock = donorGranteeApi.listDonorGrantees as unknown as Mock;
const listSessionsMock = usersApi.listSessions as unknown as Mock;
const getConsentMock = usersApi.getConsent as unknown as Mock;

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
    getAiSettingsMock.mockResolvedValue({ providers: [] });
    listDonorGranteesMock.mockResolvedValue([]);
    listSessionsMock.mockResolvedValue([]);
    getConsentMock.mockResolvedValue({
      data_processing_granted: true,
      data_processing_at: "2026-01-01T00:00:00Z",
      marketing_granted: false,
      marketing_at: null,
    });
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
});
