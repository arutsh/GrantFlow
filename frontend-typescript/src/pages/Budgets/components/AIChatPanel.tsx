import React, { useState, useRef, useEffect } from "react";
import Button from "@/components/ui/Button";
import { streamAiChat } from "@/api/budgetApi";
import { useAiChat } from "@/context/AiChatContext";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  isError?: boolean;
  isStreaming?: boolean;
}

export const WELCOME_MESSAGE: ChatMessage = {
  id: "welcome",
  role: "assistant",
  content:
    "How can I help with your budget? You can ask me to create a budget, add lines, or update existing ones.",
};

type StreamStatus =
  | { type: "idle" }
  | { type: "thinking" }
  | { type: "tool"; name: string }
  | { type: "streaming" };

export function AIChatPanel() {
  const {
    messages,
    setMessages,
    contextBudget,
    closeAi,
    sessionId,
    setSessionId,
    chatBudgetId,
    setChatBudgetId,
  } = useAiChat();

  const [input, setInput] = useState("");
  const [status, setStatus] = useState<StreamStatus>({ type: "idle" });
  const abortRef = useRef<AbortController | null>(null);
  const streamingIdRef = useRef<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const isStreaming = status.type !== "idle";

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, status]);

  const addMessage = (msg: Omit<ChatMessage, "id">) => {
    const id = crypto.randomUUID();
    setMessages((prev) => [...prev, { ...msg, id }]);
    return id;
  };

  const statusLabel = (): string => {
    switch (status.type) {
      case "thinking":
        return "Thinking...";
      case "tool":
        return `Running: ${status.name.replace(/_/g, " ")}…`;
      case "streaming":
        return "Responding…";
      default:
        return "";
    }
  };

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;

    addMessage({ role: "user", content: text });
    setInput("");
    setStatus({ type: "thinking" });

    const assistantId = addMessage({
      role: "assistant",
      content: "",
      isStreaming: true,
    });
    streamingIdRef.current = assistantId;

    abortRef.current = streamAiChat(
      text,
      sessionId,
      contextBudget?.id?.toString() ?? chatBudgetId,
      {
        onThinking: () => setStatus({ type: "thinking" }),
        onText: (delta) => {
          setStatus({ type: "streaming" });
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + delta }
                : m
            )
          );
        },
        onToolCall: (toolName) =>
          setStatus({ type: "tool", name: toolName }),
        onActionResult: () => setStatus({ type: "streaming" }),
        onDone: (response, budgetId) => {
          if (budgetId) setChatBudgetId(budgetId);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: response, isStreaming: false }
                : m
            )
          );
          streamingIdRef.current = null;
          setStatus({ type: "idle" });
        },
        onError: (message) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: message, isError: true, isStreaming: false }
                : m
            )
          );
          streamingIdRef.current = null;
          setStatus({ type: "idle" });
        },
        onUnavailable: () => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? {
                    ...m,
                    content: "AI is not available. Ask your admin to configure an API key.",
                    isError: true,
                    isStreaming: false,
                  }
                : m
            )
          );
          streamingIdRef.current = null;
          setStatus({ type: "idle" });
        },
      },
      (id) => setSessionId(id),
      "budgets",
    );
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="w-96 flex-shrink-0 border-l border-slate-200 bg-white flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-slate-800">
            AI Budget Assistant
          </span>
          <span className="w-2 h-2 rounded-full bg-green-400 flex-shrink-0" />
        </div>
        <Button
          variant="close"
          onClick={() => {
            abortRef.current?.abort();
            closeAi();
          }}
        >
          ✕
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
                msg.role === "user"
                  ? "bg-slate-800 text-white rounded-br-sm"
                  : msg.isError
                    ? "bg-red-50 text-red-700 border border-red-200 rounded-bl-sm"
                    : "bg-slate-100 text-slate-800 rounded-bl-sm"
              }`}
            >
              {msg.content}
              {msg.isStreaming && (
                <span className="inline-block w-1 h-4 ml-0.5 bg-slate-500 animate-pulse rounded-sm" />
              )}
            </div>
          </div>
        ))}

        {isStreaming && status.type !== "streaming" && (
          <div className="flex justify-start">
            <div className="bg-slate-100 rounded-2xl rounded-bl-sm px-4 py-2.5 text-sm text-slate-500 flex items-center gap-2">
              <div className="w-3 h-3 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin flex-shrink-0" />
              {statusLabel()}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-slate-200 p-4">
        <div className="flex items-end gap-2">
          <textarea
            rows={2}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isStreaming}
            placeholder={
              contextBudget
                ? "Refine this budget, e.g. 'add a travel line at £3k'..."
                : "Describe your budget or ask me to create one..."
            }
            className="flex-1 resize-none border border-slate-300 rounded-xl px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:opacity-50"
          />
          <Button
            variant="primary"
            onClick={handleSend}
            disabled={!input.trim() || isStreaming}
            className="px-3 py-2 shrink-0"
          >
            ↑
          </Button>
        </div>
        <p className="text-xs text-slate-400 mt-1.5">
          Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
