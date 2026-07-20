import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi, type Mock } from "vitest";
import { AiChatProvider, useAiChat } from "./AiChatContext";
import { AuthProvider } from "./AuthContext";
import * as chatAi from "@/api/chatApi";

vi.mock("@/api/chatApi", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/api/chatApi")>();
  return {
    ...actual,
    fetchLatestConversation: vi.fn(),
    fetchConversationMessages: vi.fn(),
  };
});

const fetchLatestConversationMock = chatAi.fetchLatestConversation as unknown as Mock;
const fetchConversationMessagesMock = chatAi.fetchConversationMessages as unknown as Mock;

function TestConsumer() {
  const { messages, conversationId, setMessages, setConversationId } = useAiChat();
  return (
    <div>
      <div data-testid="conversation-id">{conversationId ?? "none"}</div>
      <button
        onClick={() => {
          setMessages((prev) => [
            ...prev,
            { id: "local-1", role: "user", content: "add a travel line" },
          ]);
          setConversationId("local-conv");
        }}
      >
        Simulate local send
      </button>
      <ul>
        {messages.map((m) => (
          <li key={m.id}>
            {m.role}: {m.content}
          </li>
        ))}
      </ul>
    </div>
  );
}

function renderProvider() {
  return render(
    <AuthProvider>
      <AiChatProvider>
        <TestConsumer />
      </AiChatProvider>
    </AuthProvider>,
  );
}

describe("AiChatProvider history hydration", () => {
  beforeEach(() => {
    localStorage.clear();
    sessionStorage.clear();
    fetchLatestConversationMock.mockReset();
    fetchConversationMessagesMock.mockReset();
  });

  it("does not fetch history when unauthenticated", async () => {
    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId("conversation-id")).toHaveTextContent("none");
    });
    expect(fetchLatestConversationMock).not.toHaveBeenCalled();
  });

  it("rehydrates conversationId and messages when a prior conversation exists", async () => {
    localStorage.setItem("token", "fake-token");
    fetchLatestConversationMock.mockResolvedValue({
      id: "conv-1",
      title: null,
      message_count: 2,
      last_activity_at: "2026-07-20T00:00:00Z",
      created_at: "2026-07-20T00:00:00Z",
    });
    fetchConversationMessagesMock.mockResolvedValue([
      {
        id: "m1",
        role: "user",
        content: "create a budget",
        tool_name: null,
        tool_params: null,
        tool_result: null,
        created_at: "2026-07-20T00:00:00Z",
      },
      {
        id: "m2",
        role: "assistant",
        content: "Budget created successfully.",
        tool_name: "create_budget",
        tool_params: {},
        tool_result: {},
        created_at: "2026-07-20T00:00:01Z",
      },
    ]);

    renderProvider();

    await waitFor(() => {
      expect(screen.getByTestId("conversation-id")).toHaveTextContent("conv-1");
    });
    expect(screen.getByText("user: create a budget")).toBeInTheDocument();
    expect(
      screen.getByText("assistant: Budget created successfully."),
    ).toBeInTheDocument();
    expect(fetchConversationMessagesMock).toHaveBeenCalledWith("conv-1");
  });

  it("keeps the default welcome message when no prior conversation exists", async () => {
    localStorage.setItem("token", "fake-token");
    fetchLatestConversationMock.mockResolvedValue(null);

    renderProvider();

    await waitFor(() => {
      expect(fetchLatestConversationMock).toHaveBeenCalled();
    });
    expect(screen.getByTestId("conversation-id")).toHaveTextContent("none");
    expect(fetchConversationMessagesMock).not.toHaveBeenCalled();
    expect(screen.getByText(/How can I help with your budget/)).toBeInTheDocument();
  });

  it("does not clobber an in-progress local conversation when hydration resolves later", async () => {
    localStorage.setItem("token", "fake-token");

    let resolveLatest!: (value: unknown) => void;
    fetchLatestConversationMock.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveLatest = resolve;
        }),
    );
    fetchConversationMessagesMock.mockResolvedValue([
      {
        id: "old-1",
        role: "user",
        content: "old message",
        tool_name: null,
        tool_params: null,
        tool_result: null,
        created_at: "2026-07-19T00:00:00Z",
      },
    ]);

    renderProvider();

    // User sends a message locally before hydration's first fetch resolves.
    await userEvent.click(screen.getByText("Simulate local send"));
    expect(screen.getByText("user: add a travel line")).toBeInTheDocument();

    // Hydration now resolves with a stale, unrelated prior conversation.
    resolveLatest({
      id: "conv-old",
      title: null,
      message_count: 1,
      last_activity_at: "2026-07-19T00:00:00Z",
      created_at: "2026-07-19T00:00:00Z",
    });

    await waitFor(() => {
      expect(fetchConversationMessagesMock).toHaveBeenCalled();
    });

    // The user's own in-progress turn must survive, not be overwritten by
    // the late-arriving hydration result.
    expect(screen.getByText("user: add a travel line")).toBeInTheDocument();
    expect(screen.queryByText("user: old message")).not.toBeInTheDocument();
    expect(screen.getByTestId("conversation-id")).toHaveTextContent("local-conv");
  });

  it("leaves the default state if the history fetch fails", async () => {
    localStorage.setItem("token", "fake-token");
    fetchLatestConversationMock.mockRejectedValue(new Error("network error"));

    renderProvider();

    await waitFor(() => {
      expect(fetchLatestConversationMock).toHaveBeenCalled();
    });
    expect(screen.getByTestId("conversation-id")).toHaveTextContent("none");
    expect(screen.getByText(/How can I help with your budget/)).toBeInTheDocument();
  });
});
