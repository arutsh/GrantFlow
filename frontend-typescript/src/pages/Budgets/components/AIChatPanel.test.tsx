import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { vi, type Mock } from "vitest";
import { AIChatPanel } from "./AIChatPanel";
import { AiChatProvider } from "@/context/AiChatContext";
import * as chatAi from "@/api/chatApi";
import type { AiChatCallbacks } from "@/api/chatApi";

vi.mock("@/api/chatApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/chatApi")>();
  return {
    ...actual,
    streamAiChat: vi.fn(() => new AbortController()),
  };
});

const mockNavigate = vi.fn();
vi.mock("react-router-dom", async (importOriginal) => {
  const actual = await importOriginal<typeof import("react-router-dom")>();
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const streamAiChatMock = chatAi.streamAiChat as unknown as Mock;

function renderPanel(initialPath: string) {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AiChatProvider>
        <AIChatPanel />
      </AiChatProvider>
    </MemoryRouter>,
  );
}

async function sendMessage(text: string) {
  const user = userEvent.setup();
  await user.type(screen.getByRole("textbox"), text);
  await user.click(screen.getByRole("button", { name: "↑" }));
}

function lastCallbacks(): AiChatCallbacks {
  const lastCall =
    streamAiChatMock.mock.calls[streamAiChatMock.mock.calls.length - 1];
  return lastCall[3];
}

describe("AIChatPanel", () => {
  beforeEach(() => {
    streamAiChatMock.mockClear();
    mockNavigate.mockClear();
  });

  it("derives context_id and page from a budget detail URL", async () => {
    const budgetId = "550e8400-e29b-41d4-a716-446655440000";
    renderPanel(`/budgets/${budgetId}`);

    await sendMessage("add a travel line");

    expect(streamAiChatMock).toHaveBeenCalledWith(
      "add a travel line",
      null,
      budgetId,
      expect.any(Object),
      expect.any(Function),
      "budgets",
    );
  });

  it("derives a null context_id on the budgets list page", async () => {
    renderPanel("/budgets");

    await sendMessage("create a budget");

    expect(streamAiChatMock).toHaveBeenCalledWith(
      "create a budget",
      null,
      null,
      expect.any(Object),
      expect.any(Function),
      "budgets",
    );
  });

  it("derives page from the first path segment outside /budgets", async () => {
    renderPanel("/dashboard");

    await sendMessage("hello");

    expect(streamAiChatMock).toHaveBeenCalledWith(
      "hello",
      null,
      null,
      expect.any(Object),
      expect.any(Function),
      "dashboard",
    );
  });

  it("navigates to the new budget on done and never renders the raw id", async () => {
    renderPanel("/budgets");

    await sendMessage("create a budget");
    act(() => lastCallbacks().onDone("Created your budget.", "new-budget-id"));

    expect(mockNavigate).toHaveBeenCalledWith("/budgets/new-budget-id", {
      replace: true,
    });
    expect(await screen.findByText("Created your budget.")).toBeInTheDocument();
    expect(screen.queryByText(/new-budget-id/)).not.toBeInTheDocument();
  });

  it("does not navigate when done carries no budgetId", async () => {
    renderPanel("/dashboard");

    await sendMessage("what's my total spend?");
    act(() => lastCallbacks().onDone("You've spent $500 so far."));

    expect(mockNavigate).not.toHaveBeenCalled();
  });
});
