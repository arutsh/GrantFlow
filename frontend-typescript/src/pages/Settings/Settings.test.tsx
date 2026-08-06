import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import SettingsPage from "./Settings";
import * as aiSettingsApi from "@/api/aiSettingsApi";
import * as authContext from "@/context/AuthContext";
import * as donorGranteeApi from "@/api/donorGranteeApi";

vi.mock("@/api/aiSettingsApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/aiSettingsApi")>();
  return {
    ...actual,
    getAiSettings: vi.fn(),
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

function renderSettings() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <SettingsPage />
    </QueryClientProvider>,
  );
}

describe("SettingsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getAiSettingsMock.mockResolvedValue({ providers: [] });
    listDonorGranteesMock.mockResolvedValue([]);
  });

  it("does not show Manage Grantees for a non-donor customer", async () => {
    useAuthMock.mockReturnValue({ isDonor: false });
    renderSettings();

    await waitFor(() => expect(screen.getByText("Settings")).toBeInTheDocument());
    expect(screen.queryByText("Manage Grantees")).not.toBeInTheDocument();
    expect(listDonorGranteesMock).not.toHaveBeenCalled();
  });

  it("shows Manage Grantees for a donor customer", async () => {
    useAuthMock.mockReturnValue({ isDonor: true });
    renderSettings();

    await waitFor(() => expect(screen.getByText("Manage Grantees")).toBeInTheDocument());
  });
});
