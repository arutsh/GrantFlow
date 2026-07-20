import React, {
  createContext,
  useContext,
  useEffect,
  useState,
  Dispatch,
  SetStateAction,
} from "react";
import {
  ChatMessage,
  WELCOME_MESSAGE,
} from "@/pages/Budgets/components/AIChatPanel";
import { useAuth } from "@/context/AuthContext";
import { fetchLatestConversation, fetchConversationMessages } from "@/api/chatApi";

interface AiChatContextType {
  isAiOpen: boolean;
  toggleAi: () => void;
  closeAi: () => void;
  messages: ChatMessage[];
  setMessages: Dispatch<SetStateAction<ChatMessage[]>>;
  conversationId: string | null;
  setConversationId: (id: string | null) => void;
}

const AiChatContext = createContext<AiChatContextType | undefined>(undefined);

export function AiChatProvider({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth();
  const [isAiOpen, setIsAiOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME_MESSAGE]);
  const [conversationId, setConversationId] = useState<string | null>(null);

  const toggleAi = () => setIsAiOpen((v) => !v);
  const closeAi = () => setIsAiOpen(false);

  // Chat history lives server-side (chat service), not in browser state, so
  // a page reload shouldn't erase it — rehydrate the most recent conversation
  // whenever we transition into an authenticated session (covers both "still
  // logged in after a reload" and "just logged in fresh").
  //
  // The two fetches below are real network round-trips, and the panel is
  // interactable the whole time (isAiOpen is independent of this effect) —
  // a user can open the chat and send a message before hydration resolves.
  // Applying the hydration result unconditionally would then clobber
  // whatever they just typed. Both setters below use the functional-update
  // form so they only apply the fetched state if nothing has happened yet
  // (messages still just the welcome message; conversationId still unset),
  // rather than overwriting live local state with stale fetched state.
  useEffect(() => {
    if (!isAuthenticated) return;

    let cancelled = false;
    (async () => {
      try {
        const conversation = await fetchLatestConversation();
        if (!conversation || cancelled) return;

        const history = await fetchConversationMessages(conversation.id);
        if (cancelled) return;

        if (history.length > 0) {
          const hydrated: ChatMessage[] = history.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
          }));
          setMessages((prev) =>
            prev.length === 1 && prev[0].id === WELCOME_MESSAGE.id ? hydrated : prev,
          );
        }
        setConversationId((prev) => (prev === null ? conversation.id : prev));
      } catch {
        // No history to restore is not an error state — leave the default
        // welcome message and a fresh conversation.
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  return (
    <AiChatContext.Provider
      value={{
        isAiOpen,
        toggleAi,
        closeAi,
        messages,
        setMessages,
        conversationId,
        setConversationId,
      }}
    >
      {children}
    </AiChatContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAiChat(): AiChatContextType {
  const ctx = useContext(AiChatContext);
  if (!ctx) throw new Error("useAiChat must be used within AiChatProvider");
  return ctx;
}
