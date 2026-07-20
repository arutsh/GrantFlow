import { useState } from "react";
import { Eye, EyeOff, ExternalLink } from "lucide-react";
import {
  getAiSettings,
  saveAiKey,
  clearAiKey,
  ProviderStatus,
} from "@/api/aiSettingsApi";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";

// Mirrors AIModelName enum from the backend — models the platform officially supports
const SUPPORTED_MODELS = [
  { value: "claude-sonnet-4-6", label: "Claude Sonnet 4.6" },
  { value: "llama3.2", label: "Llama 3.2 (Ollama)" },
  { value: "gemma4:12b", label: "Gemma 4 (Ollama)" },
];

const PROVIDER_HELP: Record<
  string,
  { description: string; link: string; linkLabel: string }
> = {
  anthropic: {
    description:
      "Used for AI-powered budget creation. Your key is encrypted at rest and never exposed.",
    link: "https://console.anthropic.com/settings/keys",
    linkLabel: "Get an Anthropic API key",
  },
};

function ProviderCard({ provider }: { provider: ProviderStatus }) {
  const queryClient = useQueryClient();
  const [keyInput, setKeyInput] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [selectedModel, setSelectedModel] = useState(
    provider.model ?? SUPPORTED_MODELS[0].value,
  );
  const [urlInput, setUrlInput] = useState(provider.base_url ?? "");
  const [confirmClear, setConfirmClear] = useState(false);

  const saveMutation = useMutation({
    mutationFn: () =>
      saveAiKey(
        provider.name,
        provider.requires_key ? keyInput : null,
        selectedModel,
        provider.base_url !== undefined ? urlInput || null : null,
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
      setKeyInput("");
    },
  });

  const clearMutation = useMutation({
    mutationFn: () => clearAiKey(provider.name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["ai-settings"] });
      setConfirmClear(false);
    },
  });

  const canSave = provider.requires_key ? keyInput.trim().length > 0 : true;
  const help = PROVIDER_HELP[provider.name];

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-start justify-between mb-1">
        <h2 className="text-base font-semibold text-gray-900">
          {provider.display_name}
        </h2>
        <span
          className={`text-xs font-medium px-2.5 py-1 rounded-full ${
            provider.has_key
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {provider.has_key ? "Configured" : "Not configured"}
        </span>
      </div>

      {help && (
        <p className="text-sm text-gray-500 mb-5">
          {help.description}{" "}
          <a
            href={help.link}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1 text-blue-600 hover:underline"
          >
            {help.linkLabel} <ExternalLink size={12} />
          </a>
        </p>
      )}

      <div className="flex flex-col gap-3 mb-3">
        {/* Model selector */}
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Model
          </label>
          <select
            value={selectedModel}
            onChange={(e) => setSelectedModel(e.target.value)}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {SUPPORTED_MODELS.map((m) => (
              <option key={m.value} value={m.value}>
                {m.label}
              </option>
            ))}
          </select>
        </div>

        {/* API key input (key-based providers only) */}
        {provider.requires_key && (
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              API Key
            </label>
            <div className="relative">
              <input
                type={showKey ? "text" : "password"}
                value={keyInput}
                onChange={(e) => setKeyInput(e.target.value)}
                placeholder={
                  provider.has_key
                    ? "Enter new key to replace existing"
                    : "sk-ant-..."
                }
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm pr-10 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="button"
                onClick={() => setShowKey((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showKey ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>
        )}

        {/* Base URL input (URL-based providers like Ollama) */}
        {!provider.requires_key && (
          <div>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              Base URL
            </label>
            <input
              type="text"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              placeholder="http://localhost:11434"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        )}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => saveMutation.mutate()}
          disabled={!canSave || saveMutation.isPending}
          className="px-4 py-2 text-sm font-medium bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {saveMutation.isPending ? "Saving…" : "Save"}
        </button>

        {provider.has_key && !confirmClear && (
          <button
            onClick={() => setConfirmClear(true)}
            className="text-sm text-red-500 hover:text-red-700"
          >
            Remove
          </button>
        )}

        {confirmClear && (
          <>
            <span className="text-sm text-gray-600">Remove configuration?</span>
            <button
              onClick={() => clearMutation.mutate()}
              disabled={clearMutation.isPending}
              className="text-sm font-medium text-red-600 hover:text-red-800 disabled:opacity-50"
            >
              {clearMutation.isPending ? "Removing…" : "Yes, remove"}
            </button>
            <button
              onClick={() => setConfirmClear(false)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </>
        )}
      </div>

      {saveMutation.isError && (
        <p className="text-sm text-red-600 mt-3">
          {(saveMutation.error as any)?.response?.data?.detail ??
            "Failed to save"}
        </p>
      )}
    </section>
  );
}

export default function SettingsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ["ai-settings"],
    queryFn: getAiSettings,
  });

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold text-gray-900 mb-8">Settings</h1>

      {isLoading && <p className="text-sm text-gray-400">Loading…</p>}

      <div className="flex flex-col gap-4">
        {data?.providers.map((p) => (
          <ProviderCard key={p.name} provider={p} />
        ))}
      </div>
    </div>
  );
}
