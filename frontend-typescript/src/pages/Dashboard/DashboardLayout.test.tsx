import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import DashboardLayout from "./DashboardLayout";
import * as authContext from "@/context/AuthContext";
import * as aiChatContext from "@/context/AiChatContext";

vi.mock("@/context/AuthContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/context/AuthContext")>();
  return {
    ...actual,
    useAuth: vi.fn(),
  };
});

vi.mock("@/context/AiChatContext", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/context/AiChatContext")>();
  return {
    ...actual,
    useAiChat: vi.fn(),
  };
});

// The AI panel pulls in chat API/networking concerns unrelated to the nav
// shell under test here.
vi.mock("@/pages/Budgets/components/AIChatPanel", () => ({
  AIChatPanel: () => <div>AI Chat Panel</div>,
}));

const useAuthMock = authContext.useAuth as unknown as Mock;
const useAiChatMock = aiChatContext.useAiChat as unknown as Mock;

// The <aside> stays mounted (with its nav labels) at all times — only its
// transform and the scrim toggle — so drawer open/closed state is asserted
// via those, not via presence/absence of nav content.
function getScrim(container: HTMLElement): Element | null {
  return container.querySelector(".bg-black\\/50");
}

function getAside(container: HTMLElement): Element {
  const aside = container.querySelector("aside");
  if (!aside) throw new Error("aside not found");
  return aside;
}

function renderWithProviders(children: ReactNode) {
  const queryClient = new QueryClient();
  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <DashboardLayout>{children}</DashboardLayout>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

function renderLayout() {
  return renderWithProviders(<div>Page content</div>);
}

describe("DashboardLayout", () => {
  beforeEach(() => {
    useAuthMock.mockReturnValue({
      isDonor: false,
      isImpersonating: false,
      impersonatedCustomerName: null,
      exitImpersonation: vi.fn(),
    });
    useAiChatMock.mockReturnValue({ isAiOpen: false, toggleAi: vi.fn() });
  });

  it("is off-canvas with no scrim by default", () => {
    const { container } = renderLayout();

    expect(getAside(container).className).toContain("-translate-x-full");
    expect(getScrim(container)).toBeNull();
  });

  it("opens the drawer when the top bar's menu button is pressed", async () => {
    const user = userEvent.setup();
    const { container } = renderLayout();

    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));

    expect(getAside(container).className).not.toContain("-translate-x-full");
    expect(getScrim(container)).not.toBeNull();
  });

  it("closes the drawer via its close control", async () => {
    const user = userEvent.setup();
    const { container } = renderLayout();

    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));
    await user.click(screen.getByRole("button", { name: "Close navigation menu" }));

    expect(getAside(container).className).toContain("-translate-x-full");
    expect(getScrim(container)).toBeNull();
  });

  it("closes the drawer when tapping the scrim outside it", async () => {
    const user = userEvent.setup();
    const { container } = renderLayout();

    await user.click(screen.getByRole("button", { name: "Open navigation menu" }));
    const scrim = getScrim(container);
    expect(scrim).not.toBeNull();

    await user.click(scrim as Element);

    expect(getAside(container).className).toContain("-translate-x-full");
    expect(getScrim(container)).toBeNull();
  });

  it("always renders page content and the desktop nav labels regardless of drawer state", () => {
    renderLayout();

    expect(screen.getByText("Page content")).toBeInTheDocument();
    expect(screen.getByText("Dashboard")).toBeInTheDocument();
  });

  it("does not render the impersonation banner outside an active session", () => {
    renderLayout();

    expect(screen.queryByRole("button", { name: "Exit impersonation" })).not.toBeInTheDocument();
  });

  it("renders the impersonation banner above TopBar, naming the customer, whenever a session is active", () => {
    useAuthMock.mockReturnValue({
      isDonor: false,
      isImpersonating: true,
      impersonatedCustomerName: "Acme NGO",
      exitImpersonation: vi.fn(),
    });

    renderLayout();

    expect(screen.getByText(/Acme NGO/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Exit impersonation" })).toBeInTheDocument();
  });

  it("keeps the banner mounted across a route change, since it's rendered above the swapped page content", () => {
    useAuthMock.mockReturnValue({
      isDonor: false,
      isImpersonating: true,
      impersonatedCustomerName: "Acme NGO",
      exitImpersonation: vi.fn(),
    });

    const queryClient = new QueryClient();
    const { rerender } = render(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <DashboardLayout>
            <div>Budgets page</div>
          </DashboardLayout>
        </QueryClientProvider>
      </MemoryRouter>,
    );
    expect(screen.getByText(/Acme NGO/)).toBeInTheDocument();

    rerender(
      <MemoryRouter>
        <QueryClientProvider client={queryClient}>
          <DashboardLayout>
            <div>Reports page</div>
          </DashboardLayout>
        </QueryClientProvider>
      </MemoryRouter>,
    );

    expect(screen.getByText("Reports page")).toBeInTheDocument();
    expect(screen.getByText(/Acme NGO/)).toBeInTheDocument();
  });
});
