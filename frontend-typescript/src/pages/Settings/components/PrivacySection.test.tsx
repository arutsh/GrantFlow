import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { vi, type Mock } from "vitest";
import { PrivacySection } from "./PrivacySection";
import * as usersApi from "@/api/usersApi";
import * as authContext from "@/context/AuthContext";

vi.mock("@/api/usersApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/usersApi")>();
  return {
    ...actual,
    getConsent: vi.fn(),
  };
});

// DeleteAccountButton calls useAuth() for the token/logout it needs on
// confirm — not exercised by these tests, so a minimal stub is enough.
vi.mock("@/context/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/context/AuthContext")>();
  return {
    ...actual,
    useAuth: vi.fn(),
  };
});

const getConsentMock = usersApi.getConsent as unknown as Mock;
const useAuthMock = authContext.useAuth as unknown as Mock;

function renderPrivacySection() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <PrivacySection />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("PrivacySection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthMock.mockReturnValue({ token: "fake-token", logout: vi.fn() });
  });

  it("shows data-processing consent as granted with its timestamp", async () => {
    getConsentMock.mockResolvedValue({
      data_processing_granted: true,
      data_processing_at: "2026-01-01T00:00:00Z",
      marketing_granted: false,
      marketing_at: null,
    });
    renderPrivacySection();

    await waitFor(() => expect(screen.getByText("Data processing")).toBeInTheDocument());
    expect(screen.getByText(/granted/)).toBeInTheDocument();
  });

  it("shows marketing consent as granted with its timestamp when subscribed", async () => {
    getConsentMock.mockResolvedValue({
      data_processing_granted: true,
      data_processing_at: "2026-01-01T00:00:00Z",
      marketing_granted: true,
      marketing_at: "2026-02-01T00:00:00Z",
    });
    renderPrivacySection();

    await waitFor(() => expect(screen.getByText(/Subscribed.*since/)).toBeInTheDocument());
  });
});
