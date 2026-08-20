import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import { AuthProvider } from "@/context/AuthContext";
import VerifyEmail from "./VerifyEmail";

vi.mock("@/api/usersApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/usersApi")>();
  return {
    ...actual,
    verifyEmail: vi.fn(),
  };
});

import { verifyEmail } from "@/api/usersApi";

function renderAt(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <MemoryRouter initialEntries={[path]}>
          <Routes>
            <Route path="/verify-email" element={<VerifyEmail />} />
          </Routes>
        </MemoryRouter>
      </AuthProvider>
    </QueryClientProvider>,
  );
}

describe("VerifyEmail", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    vi.mocked(verifyEmail).mockReset();
  });

  it("shows an invalid-link message when the URL has no token", async () => {
    renderAt("/verify-email");

    expect(await screen.findByText("Invalid link")).toBeInTheDocument();
    expect(verifyEmail).not.toHaveBeenCalled();
  });

  it("shows an invalid-link message when the URL has a token but no email", async () => {
    renderAt("/verify-email?token=good-token");

    expect(await screen.findByText("Invalid link")).toBeInTheDocument();
    expect(verifyEmail).not.toHaveBeenCalled();
  });

  it("shows success and continues on a valid token+email", async () => {
    vi.mocked(verifyEmail).mockResolvedValue({
      email_verified: true,
      access_token: "new-access-token",
      refresh_token: "new-refresh-token",
      status: "pending",
    });

    renderAt("/verify-email?token=good-token&email=user%40example.com");

    await waitFor(() => {
      expect(screen.getByText("Email confirmed")).toBeInTheDocument();
    });
    expect(verifyEmail).toHaveBeenCalledWith("user@example.com", "good-token");
  });

  it("logs the user in with the tokens returned by verify-email", async () => {
    vi.mocked(verifyEmail).mockResolvedValue({
      email_verified: true,
      access_token: "new-access-token",
      refresh_token: "new-refresh-token",
      status: "pending",
    });

    renderAt("/verify-email?token=good-token&email=user%40example.com");

    await waitFor(() => {
      expect(sessionStorage.getItem("token")).toBe("new-access-token");
    });
    expect(sessionStorage.getItem("refreshToken")).toBe("new-refresh-token");
  });

  it("shows an error state when the token is expired or already used", async () => {
    vi.mocked(verifyEmail).mockRejectedValue(new Error("expired"));

    renderAt("/verify-email?token=bad-token&email=user%40example.com");

    await waitFor(() => {
      expect(
        screen.getByText("Link expired or already used"),
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText("Resend confirmation email"),
    ).toBeInTheDocument();
  });
});
