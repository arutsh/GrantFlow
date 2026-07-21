import { render, screen, waitFor } from "@testing-library/react";
import { AuthProvider, useAuth } from "./AuthContext";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import App from "@/App";

function makeFakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

function TestComponent() {
  const { isAuthenticated, isNgo, isDonor, login, logout, username } =
    useAuth();
  return (
    <div>
      <div>Auth: {isAuthenticated ? "Yes" : "No"}</div>
      <div data-testid="is-ngo">{String(isNgo)}</div>
      <div data-testid="is-donor">{String(isDonor)}</div>
      <button
        onClick={() =>
          login("fake-token", "john", true, "active", "refresh-token")
        }
      >
        LoginRemember
      </button>
      <button
        onClick={() =>
          login("fake-token", "john", false, "active", "refresh-token")
        }
      >
        Login
      </button>
      <button
        onClick={() =>
          login(
            makeFakeJwt({ is_donor: true }),
            "john",
            true,
            "active",
            "refresh-token",
          )
        }
      >
        LoginDonor
      </button>
      <button
        onClick={() =>
          login(
            makeFakeJwt({ is_ngo: true, is_donor: true }),
            "john",
            true,
            "active",
            "refresh-token",
          )
        }
      >
        LoginNgoAndDonor
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

describe("AuthProvider", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("starts unauthenticated", () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );
    expect(screen.getByText("Auth: No")).toBeInTheDocument();
  });

  it("should login and persist token in localStorage when remember=true", async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    userEvent.click(screen.getByText("LoginRemember"));

    await waitFor(() => {
      expect(screen.getByText("Auth: Yes")).toBeInTheDocument();
    });

    expect(localStorage.getItem("token")).toBe("fake-token");
  });

  it("should login and persist token in sessionStorage when remember=false", async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    userEvent.click(screen.getByText("Login"));

    await waitFor(() => {
      expect(screen.getByText("Auth: Yes")).toBeInTheDocument();
    });

    expect(sessionStorage.getItem("token")).toBe("fake-token");
  });

  it("should logout and clear storage", async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    userEvent.click(screen.getByText("Login"));

    await waitFor(() => screen.getByText(/Auth: yes/i));

    userEvent.click(screen.getByText("Logout"));

    await waitFor(() => {
      expect(screen.getByText(/Auth: no/i)).toBeInTheDocument();
    });
    expect(localStorage.getItem("token")).toBeNull();
  });

  it("defaults isNgo/isDonor to false when unauthenticated", () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );
    expect(screen.getByTestId("is-ngo")).toHaveTextContent("false");
    expect(screen.getByTestId("is-donor")).toHaveTextContent("false");
  });

  it("derives isDonor from the decoded token after login", async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    userEvent.click(screen.getByText("LoginDonor"));

    await waitFor(() => {
      expect(screen.getByTestId("is-donor")).toHaveTextContent("true");
    });
    expect(screen.getByTestId("is-ngo")).toHaveTextContent("false");
  });

  it("derives both isNgo and isDonor for a customer holding both roles", async () => {
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    userEvent.click(screen.getByText("LoginNgoAndDonor"));

    await waitFor(() => {
      expect(screen.getByTestId("is-ngo")).toHaveTextContent("true");
    });
    expect(screen.getByTestId("is-donor")).toHaveTextContent("true");
  });

  it("re-derives flags from a token already persisted in storage on mount", async () => {
    localStorage.setItem("token", makeFakeJwt({ is_donor: true }));
    localStorage.setItem("username", "john");

    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>,
    );

    await waitFor(() => {
      expect(screen.getByText("Auth: Yes")).toBeInTheDocument();
    });
    expect(screen.getByTestId("is-donor")).toHaveTextContent("true");
    expect(screen.getByTestId("is-ngo")).toHaveTextContent("false");
  });
});
