import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi } from "vitest";
import AcceptInvite from "./AcceptInvite";
import * as adminManagementApi from "@/api/adminManagementApi";

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderPage(search: string) {
  const queryClient = new QueryClient();
  return render(
    <MemoryRouter initialEntries={[`/accept-invite${search}`]}>
      <QueryClientProvider client={queryClient}>
        <Routes>
          <Route path="/accept-invite" element={<AcceptInvite />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("AcceptInvite", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    vi.restoreAllMocks();
  });

  it("shows an invalid-link message when the token or email is missing", () => {
    renderPage("");

    expect(screen.getByText("Invalid link")).toBeInTheDocument();
  });

  it("submits the token, email, and chosen password, then navigates to login", async () => {
    const user = userEvent.setup();
    const acceptMock = vi
      .spyOn(adminManagementApi, "acceptInvite")
      .mockResolvedValue({ email_verified: true });

    renderPage("?token=abc123&email=new%40example.com");

    await user.type(screen.getByLabelText(/Password/), "correct-horse-1");
    await user.click(screen.getByRole("button", { name: "Set password and continue" }));

    await waitFor(() => {
      expect(acceptMock).toHaveBeenCalledWith("new@example.com", "abc123", "correct-horse-1");
    });
    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith("/login");
    });
  });

  it("shows an error when the invite is invalid or expired", async () => {
    const user = userEvent.setup();
    vi.spyOn(adminManagementApi, "acceptInvite").mockRejectedValue(new Error("bad token"));

    renderPage("?token=abc123&email=new%40example.com");

    await user.type(screen.getByLabelText(/Password/), "correct-horse-1");
    await user.click(screen.getByRole("button", { name: "Set password and continue" }));

    expect(
      await screen.findByText("This invitation link is invalid or has expired."),
    ).toBeInTheDocument();
  });
});
