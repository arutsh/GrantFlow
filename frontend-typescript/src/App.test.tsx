import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "@/App";

function makeFakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

function renderAppAt(path: string) {
  window.history.pushState({}, "", path);
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

describe("onboarding email-verification gate", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
  });

  it("redirects an unverified user away from onboarding to the confirm-email screen", async () => {
    localStorage.setItem(
      "token",
      makeFakeJwt({ user_id: "u1", email_verified: false }),
    );
    localStorage.setItem("username", "john@example.com");
    sessionStorage.setItem("status", "pending");

    renderAppAt("/onboarding");

    await waitFor(() => {
      expect(screen.getByText("Check your email")).toBeInTheDocument();
    });
  });

  it("lets a verified user reach onboarding as before", async () => {
    localStorage.setItem(
      "token",
      makeFakeJwt({ user_id: "u1", email_verified: true }),
    );
    localStorage.setItem("username", "john@example.com");
    sessionStorage.setItem("status", "pending");

    renderAppAt("/onboarding");

    await waitFor(() => {
      expect(screen.getByText("Tell us about you")).toBeInTheDocument();
    });
  });
});
