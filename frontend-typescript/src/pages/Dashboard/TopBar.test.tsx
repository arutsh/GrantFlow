import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { TopBar } from "./TopBar";
import { AuthProvider } from "@/context/AuthContext";

function makeFakeJwt(payload: Record<string, unknown>): string {
  const header = btoa(JSON.stringify({ alg: "none", typ: "JWT" }));
  const body = btoa(JSON.stringify(payload));
  return `${header}.${body}.signature`;
}

function renderTopBar(onOpenMenu: () => void = () => {}) {
  localStorage.setItem("token", makeFakeJwt({ is_ngo: true }));
  localStorage.setItem("username", "Jane Doe");
  return render(
    <MemoryRouter>
      <AuthProvider>
        <TopBar onOpenMenu={onOpenMenu} />
      </AuthProvider>
    </MemoryRouter>,
  );
}

describe("TopBar", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("shows the user's name and initials, menu closed by default", () => {
    renderTopBar();

    expect(screen.getByText("Jane Doe")).toBeInTheDocument();
    expect(screen.getByText("JD")).toBeInTheDocument();
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("opens the menu on click, showing a disabled Account Settings item and an active Logout item", async () => {
    const user = userEvent.setup();
    renderTopBar();

    await user.click(screen.getByRole("button", { name: /Jane Doe/i }));

    expect(screen.getByRole("menu")).toBeInTheDocument();
    const settingsItem = screen.getByRole("menuitem", { name: "Account Settings" });
    expect(settingsItem).toBeDisabled();
    expect(screen.getByRole("menuitem", { name: "Logout" })).toBeEnabled();
  });

  it("closes the menu when clicking outside", async () => {
    const user = userEvent.setup();
    renderTopBar();

    await user.click(screen.getByRole("button", { name: /Jane Doe/i }));
    expect(screen.getByRole("menu")).toBeInTheDocument();

    await user.click(document.body);
    expect(screen.queryByRole("menu")).not.toBeInTheDocument();
  });

  it("logs out and clears stored credentials when Logout is clicked", async () => {
    const user = userEvent.setup();
    renderTopBar();

    await user.click(screen.getByRole("button", { name: /Jane Doe/i }));
    await user.click(screen.getByRole("menuitem", { name: "Logout" }));

    expect(localStorage.getItem("token")).toBeNull();
  });

  it("calls onOpenMenu when the mobile menu button is pressed", async () => {
    const user = userEvent.setup();
    const onOpenMenu = vi.fn();
    renderTopBar(onOpenMenu);

    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));

    expect(onOpenMenu).toHaveBeenCalledTimes(1);
  });
});
