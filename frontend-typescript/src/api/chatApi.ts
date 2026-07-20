import { getAuthToken } from "@/api/axiosConfig";
import gatewayApi, { GATEWAY_BASE_URL } from "./gatewayApi";

export interface ConversationSummary {
  id: string;
  title: string | null;
  message_count: number;
  last_activity_at: string;
  created_at: string;
}

export interface ConversationMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tool_name: string | null;
  tool_params: Record<string, unknown> | null;
  tool_result: Record<string, unknown> | null;
  created_at: string;
}

// Any-device conversation retrieval (specs/chat-conversations.md) — used to
// rehydrate the visible transcript on app load instead of losing it on
// every page reload, since the chat service (not the browser) is the source
// of truth for history.
export const fetchLatestConversation = async (): Promise<ConversationSummary | null> => {
  const { data } = await gatewayApi.get<ConversationSummary[]>("/chat/conversations", {
    params: { limit: 1 },
  });
  return data[0] ?? null;
};

export const fetchConversationMessages = async (
  conversationId: string,
): Promise<ConversationMessage[]> => {
  const { data } = await gatewayApi.get<ConversationMessage[]>(
    `/chat/conversations/${conversationId}/messages`,
  );
  return data;
};

export type AiChatCallbacks = {
  onThinking?: () => void;
  onText: (delta: string) => void;
  onToolCall?: (toolName: string) => void;
  onActionResult?: (toolName: string, output: string) => void;
  onDone: (response: string, budgetId?: string) => void;
  onError: (message: string) => void;
  onUnavailable: () => void;
};

export const streamAiChat = (
  message: string,
  conversationId: string | null,
  contextId: string | null,
  callbacks: AiChatCallbacks,
  onConversationId: (id: string) => void,
  page?: string,
): AbortController => {
  const controller = new AbortController();
  const token = getAuthToken();

  (async () => {
    try {
      const response = await fetch(`${GATEWAY_BASE_URL}/chat/stream`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          context_id: contextId,
          page: page ?? null,
        }),
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        callbacks.onError("Service error");
        return;
      }

      const cid = response.headers.get("x-conversation-id");
      if (cid) onConversationId(cid);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";
      let textAccumulator = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            const raw = line.slice(6);
            try {
              const data = JSON.parse(raw) as Record<string, string>;
              switch (currentEvent) {
                case "thinking":
                  callbacks.onThinking?.();
                  break;
                case "text":
                  textAccumulator += data.delta ?? "";
                  callbacks.onText(data.delta ?? "");
                  break;
                case "tool_call":
                  callbacks.onToolCall?.(data.tool_name ?? "");
                  break;
                case "action_result":
                  callbacks.onActionResult?.(
                    data.tool_name ?? "",
                    data.output ?? "",
                  );
                  break;
                case "done":
                  callbacks.onDone(
                    data.response ?? textAccumulator,
                    data.budget_id,
                  );
                  break;
                case "error":
                  callbacks.onError(data.message ?? "AI service error");
                  break;
                case "unavailable":
                  callbacks.onUnavailable();
                  break;
              }
            } catch {
              // ignore malformed data lines
            }
            currentEvent = "";
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        callbacks.onError("Connection failed");
      }
    }
  })();

  return controller;
};
