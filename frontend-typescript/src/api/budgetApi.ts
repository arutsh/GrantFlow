import {
  BudgetUpdate,
  Budget,
  ParseBudgetResponse,
  CreateBudgetWithLinesRequest,
} from "@/pages/Budgets/types/budget";
import gatewayApi, { GATEWAY_BASE_URL } from "@/api/gatewayApi";
import { getAuthToken } from "@/api/axiosConfig";

const AI_API_BASE =
  import.meta.env.VITE_AI_SERVICE_URL ||
  import.meta.env.VITE_API_GATEWAY ||
  "http://localhost:8082/api/v1";

export const editBudget = async (
  id: string,
  budgetData: BudgetUpdate
): Promise<Budget> => {
  const { data } = await gatewayApi.patch(`/budgets/${id}`, budgetData);
  return data;
};

export const deleteBudget = async (id: string) => {
  const { data } = await gatewayApi.delete(`/budgets/${id}`);
  return data;
};

export const archiveBudget = async (id: string) => {
  const { data } = await gatewayApi.patch(`/budgets/${id}`, {
    status: "archived",
  });
  return data;
};

export const createBudget = async (
  budgetData: BudgetUpdate
): Promise<Budget> => {
  const { data } = await gatewayApi.post(`/budgets/`, budgetData);
  return data;
};

export const createBudgetWithLines = async (
  req: CreateBudgetWithLinesRequest
): Promise<Budget> => {
  const { data } = await gatewayApi.post("/budgets/with-lines", req);
  return data;
};

export const streamAiCreateBudget = (
  text: string,
  onProgress: (status: string) => void,
  onCreated: (budgetId: string) => void,
  onError: (message: string) => void,
  onUnavailable: () => void
): AbortController => {
  const controller = new AbortController();
  const token = getAuthToken();

  (async () => {
    try {
      const response = await fetch(
        `${GATEWAY_BASE_URL}/budgets/ai/stream`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ text }),
          signal: controller.signal,
        }
      );

      if (!response.ok || !response.body) {
        onError("Service error");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";

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
            const data = line.slice(6);
            if (currentEvent === "progress") {
              try {
                const parsed = JSON.parse(data) as { status: string };
                onProgress(parsed.status);
              } catch {
                // ignore malformed
              }
            } else if (currentEvent === "created") {
              try {
                const parsed = JSON.parse(data) as { budget_id: string };
                onCreated(parsed.budget_id);
              } catch {
                onError("Invalid response from server");
              }
            } else if (currentEvent === "error") {
              try {
                const parsed = JSON.parse(data) as { message?: string; detail?: string };
                onError(parsed.detail || parsed.message || "AI service error");
              } catch {
                onError(data || "AI service error");
              }
            } else if (currentEvent === "unavailable") {
              onUnavailable();
            }
            currentEvent = "";
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        onError("Connection failed");
      }
    }
  })();

  return controller;
};

export const streamParseBudget = (
  text: string,
  onProgress: (status: string) => void,
  onDone: (response: ParseBudgetResponse) => void,
  onError: (message: string) => void,
  onUnavailable: () => void
): AbortController => {
  const controller = new AbortController();
  const token = getAuthToken();
  const url = `${AI_API_BASE}/ai/parse-budget/stream?text=${encodeURIComponent(text)}`;

  (async () => {
    try {
      const response = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });

      if (!response.ok || !response.body) {
        onError("Service error");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let currentEvent = "";

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
            const data = line.slice(6);
            if (currentEvent === "progress") {
              try {
                const parsed = JSON.parse(data) as { status: string };
                onProgress(parsed.status);
              } catch {
                // ignore malformed progress event
              }
            } else if (currentEvent === "done") {
              try {
                onDone(JSON.parse(data) as ParseBudgetResponse);
              } catch {
                onError("Invalid response from AI service");
              }
            } else if (currentEvent === "error") {
              onError(data || "AI service error");
            } else if (currentEvent === "unavailable") {
              onUnavailable();
            }
            currentEvent = "";
          }
        }
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
        onError("Connection to AI service failed");
      }
    }
  })();

  return controller;
};
