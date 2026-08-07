import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
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

function renderLayout() {
  return render(
    <MemoryRouter>
      <DashboardLayout>
        <div>Page content</div>
      </DashboardLayout>
    </MemoryRouter>,
  );
}

describe("DashboardLayout", () => {
  beforeEach(() => {
    useAuthMock.mockReturnValue({ isDonor: false });
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
});
