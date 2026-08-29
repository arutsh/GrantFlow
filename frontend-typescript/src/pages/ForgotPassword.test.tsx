import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import ForgotPassword from "./ForgotPassword";

vi.mock("@/api/usersApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/usersApi")>();
  return { ...actual, forgotPassword: vi.fn() };
});

import { forgotPassword } from "@/api/usersApi";

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ForgotPassword />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ForgotPassword", () => {
  beforeEach(() => {
    vi.mocked(forgotPassword).mockReset();
  });

  it("shows the same generic confirmation on a successful request", async () => {
    vi.mocked(forgotPassword).mockResolvedValue({ sent: true });
    const user = userEvent.setup();

    renderPage();
    await user.type(screen.getByPlaceholderText(/enter your email/i), "user@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByText("Check your email")).toBeInTheDocument();
    });
    expect(forgotPassword).toHaveBeenCalledWith("user@example.com");
  });

  it("shows the same generic confirmation even when the request errors", async () => {
    // No enumeration signal in the UI — a failure looks identical to success.
    vi.mocked(forgotPassword).mockRejectedValue(new Error("network error"));
    const user = userEvent.setup();

    renderPage();
    await user.type(screen.getByPlaceholderText(/enter your email/i), "nobody@example.com");
    await user.click(screen.getByRole("button", { name: "Send reset link" }));

    await waitFor(() => {
      expect(screen.getByText("Check your email")).toBeInTheDocument();
    });
  });
});
