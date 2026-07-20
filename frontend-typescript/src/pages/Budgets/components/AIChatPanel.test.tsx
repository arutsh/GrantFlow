import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { vi, type Mock } from "vitest";
import { AIChatPanel } from "./AIChatPanel";
import { AiChatProvider } from "@/context/AiChatContext";
import { AuthProvider } from "@/context/AuthContext";
import * as chatAi from "@/api/chatApi";
import type { AiChatCallbacks } from "@/api/chatApi";

vi.mock("@/api/chatApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/chatApi")>();
  return {
    ...actual,
    streamAiChat: vi.fn(() => new AbortController()),
    // Not under test here (see AiChatContext.test.tsx) — stubbed so an
    // authenticated render never fires a real history-hydration network call.
    fetchLatestConversation: vi.fn(() => Promise.resolve(null)),
    fetchConversationMessages: vi.fn(() => Promise.resolve([])),
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
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
  const result = render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <AuthProvider>
          <AiChatProvider>
            <AIChatPanel />
          </AiChatProvider>
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return { ...result, invalidateSpy };
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

  it("invalidates the budget query on action_result when a budget is in view", async () => {
    const budgetId = "550e8400-e29b-41d4-a716-446655440000";
    const { invalidateSpy } = renderPanel(`/budgets/${budgetId}`);

    await sendMessage("add a travel line");
    act(() => lastCallbacks().onActionResult?.("add_budget_line", "Line added."));

    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ["budgetDetails", budgetId] });
  });

  it("does not invalidate any query on action_result without a budget in view", async () => {
    const { invalidateSpy } = renderPanel("/dashboard");

    await sendMessage("hello");
    act(() => lastCallbacks().onActionResult?.("create_budget", "Budget created."));

    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it("does not invalidate the viewed budget when create_budget runs for a different one", async () => {
    // create_budget is a creating_tool, not a targeted_tool — it can execute
    // while an unrelated budget is the active contextId. Its action_result
    // must not invalidate whatever budget happens to be in view.
    const viewedBudgetId = "550e8400-e29b-41d4-a716-446655440000";
    const { invalidateSpy } = renderPanel(`/budgets/${viewedBudgetId}`);

    await sendMessage("create a totally different budget");
    act(() => lastCallbacks().onActionResult?.("create_budget", "Budget created."));

    expect(invalidateSpy).not.toHaveBeenCalled();
  });

  it("does not invalidate on a read-only get_budget_summary action_result", async () => {
    const budgetId = "550e8400-e29b-41d4-a716-446655440000";
    const { invalidateSpy } = renderPanel(`/budgets/${budgetId}`);

    await sendMessage("summarise this budget");
    act(() => lastCallbacks().onActionResult?.("get_budget_summary", "1 line, total 500."));

    expect(invalidateSpy).not.toHaveBeenCalled();
  });
});
