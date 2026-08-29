import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import Login from "./Login";
import * as usersApi from "@/api/usersApi";
import * as authContext from "@/context/AuthContext";

const mockNavigate = vi.fn();

vi.mock("@/api/usersApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/usersApi")>();
  return { ...actual, loginUser: vi.fn() };
});

vi.mock("@/context/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/context/AuthContext")>();
  return { ...actual, useAuth: vi.fn() };
});

vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return { ...actual, useNavigate: () => mockNavigate };
});

function renderLogin(initialEntries?: { pathname: string; state?: unknown }[]) {
  vi.mocked(authContext.useAuth).mockReturnValue({
    isAuthenticated: false,
    isRegistering: false,
    login: vi.fn(),
  } as any);
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Login />
    </MemoryRouter>,
  );
}

async function submit() {
  await userEvent.type(screen.getByPlaceholderText(/enter your username/i), "user@example.com");
  await userEvent.type(screen.getByPlaceholderText(/enter your password/i), "whatever");
  await userEvent.click(screen.getByRole("button", { name: /login/i }));
}

describe("Login error messages", () => {
  it("shows the server's lockout message on a 429", async () => {
    vi.mocked(usersApi.loginUser).mockRejectedValue({
      response: { status: 429, data: { detail: "Too many failed login attempts. Try again later." } },
    });
    renderLogin();
    await submit();
    expect(
      await screen.findByText("Too many failed login attempts. Try again later."),
    ).toBeInTheDocument();
  });

  it("shows a generic invalid-credentials message on a 401", async () => {
    vi.mocked(usersApi.loginUser).mockRejectedValue({
      response: { status: 401, data: { detail: "Invalid credentials" } },
    });
    renderLogin();
    await submit();
    expect(await screen.findByText("Invalid username or password")).toBeInTheDocument();
  });

  it("routes to /confirm-email on a 403 email_not_verified response", async () => {
    vi.mocked(usersApi.loginUser).mockRejectedValue({
      response: { status: 403, data: { detail: "email_not_verified" } },
    });
    renderLogin();
    await submit();
    await vi.waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/confirm-email", {
        state: { email: "user@example.com" },
      });
    });
  });
});

describe("Login success message", () => {
  it("shows the message passed via navigation state (e.g. after a password reset)", () => {
    renderLogin([
      { pathname: "/login", state: { message: "Password reset. Please log in with your new password." } },
    ]);

    expect(
      screen.getByText("Password reset. Please log in with your new password."),
    ).toBeInTheDocument();
  });

  it("has a Forgot password? link", () => {
    renderLogin();

    expect(screen.getByRole("link", { name: "Forgot password?" })).toHaveAttribute(
      "href",
      "/forgot-password",
    );
  });
});
