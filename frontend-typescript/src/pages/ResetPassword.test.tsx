import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import ResetPassword from "./ResetPassword";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock("@/api/usersApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/usersApi")>();
  return { ...actual, resetPassword: vi.fn() };
});

import { resetPassword } from "@/api/usersApi";

function renderAt(path: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/reset-password" element={<ResetPassword />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function fillAndSubmit(newPassword: string, confirmPassword: string) {
  const user = userEvent.setup();
  await user.type(screen.getByPlaceholderText(/enter a new password/i), newPassword);
  await user.type(screen.getByPlaceholderText(/confirm your new password/i), confirmPassword);
  await user.click(screen.getByRole("button", { name: "Reset password" }));
}

describe("ResetPassword", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    vi.mocked(resetPassword).mockReset();
  });

  it("shows an invalid-link message when the URL has no token or email", () => {
    renderAt("/reset-password");

    expect(screen.getByText("Invalid link")).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it("resets the password and redirects to login on success", async () => {
    vi.mocked(resetPassword).mockResolvedValue({ reset: true });

    renderAt("/reset-password?token=good-token&email=user%40example.com");
    await fillAndSubmit("N3w-Str0ng-Pass!", "N3w-Str0ng-Pass!");

    await waitFor(() => {
      expect(resetPassword).toHaveBeenCalledWith(
        "user@example.com",
        "good-token",
        "N3w-Str0ng-Pass!",
      );
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login", {
        state: { message: "Password reset. Please log in with your new password." },
      });
    });
  });

  it("rejects mismatched passwords client-side without calling the API", async () => {
    renderAt("/reset-password?token=good-token&email=user%40example.com");
    await fillAndSubmit("N3w-Str0ng-Pass!", "something-else");

    expect(await screen.findByText("Passwords do not match")).toBeInTheDocument();
    expect(resetPassword).not.toHaveBeenCalled();
  });

  it("shows an expired-link state distinct from a weak-password error", async () => {
    vi.mocked(resetPassword).mockRejectedValue({
      isAxiosError: true,
      response: { data: { detail: "Invalid or expired reset token" } },
    });

    renderAt("/reset-password?token=stale-token&email=user%40example.com");
    await fillAndSubmit("N3w-Str0ng-Pass!", "N3w-Str0ng-Pass!");

    expect(await screen.findByText("Link expired or already used")).toBeInTheDocument();
    expect(screen.getByText("Request a new reset link")).toBeInTheDocument();
  });

  it("shows the server's password-strength message inline, keeping the form", async () => {
    vi.mocked(resetPassword).mockRejectedValue({
      isAxiosError: true,
      response: { data: { detail: "Password is too common" } },
    });

    renderAt("/reset-password?token=good-token&email=user%40example.com");
    await fillAndSubmit("N3w-Str0ng-Pass!", "N3w-Str0ng-Pass!");

    expect(await screen.findByText("Password is too common")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reset password" })).toBeInTheDocument();
  });
});
