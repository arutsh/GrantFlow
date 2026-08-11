import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { SectionHead } from "@/components/ui/SectionHead";
import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { getUserIdFromToken } from "@/utils/token";
import {
  getConsent,
  updateMarketingConsent,
  exportMyData,
  deleteMyAccount,
  requestEmailChange,
} from "@/api/usersApi";

function formatDate(iso: string | null): string | null {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function ConsentSummary() {
  const { data, isLoading } = useQuery({
    queryKey: ["consent"],
    queryFn: getConsent,
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading…</p>;

  const dataProcessingAt = formatDate(data?.data_processing_at ?? null);

  return (
    <div className="max-w-md">
      <p className="text-sm font-medium text-gray-900">Data processing</p>
      <p className="text-xs text-gray-500">
        {data?.data_processing_granted
          ? `Required to use GrandFlow — granted${dataProcessingAt ? ` on ${dataProcessingAt}` : ""}.`
          : "Not granted."}
      </p>
    </div>
  );
}

function MarketingConsentToggle() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["consent"],
    queryFn: getConsent,
  });

  const mutation = useMutation({
    mutationFn: (marketing: boolean) => updateMarketingConsent(marketing),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["consent"] });
    },
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading…</p>;

  // Only a "granted at" timestamp exists — withdrawing clears it rather than
  // recording when (design.md decision 1: current/last-known state only, no
  // separate consent-change history for v1), so there's no "withdrawn on
  // <date>" to show here yet.
  const marketingAt = formatDate(data?.marketing_at ?? null);

  return (
    <div className="flex items-center justify-between max-w-md">
      <div>
        <p className="text-sm font-medium text-gray-900">Marketing emails</p>
        <p className="text-xs text-gray-500">
          {data?.marketing_granted
            ? `Subscribed to occasional product updates${marketingAt ? ` since ${marketingAt}` : ""}.`
            : "You're not subscribed to marketing emails."}
        </p>
      </div>
      <Button
        variant={data?.marketing_granted ? "toggle" : "outline"}
        active={data?.marketing_granted}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate(!data?.marketing_granted)}
      >
        {data?.marketing_granted ? "Subscribed" : "Subscribe"}
      </Button>
    </div>
  );
}

function ChangeEmailForm() {
  const [newEmail, setNewEmail] = useState("");
  const mutation = useMutation({
    mutationFn: () => requestEmailChange(newEmail),
    onSuccess: () => setNewEmail(""),
  });

  const serverError = (
    mutation.error as { response?: { data?: { detail?: string } } }
  )?.response?.data?.detail;

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        mutation.mutate();
      }}
      className="flex flex-col gap-2 max-w-sm"
    >
      <label className="block text-xs font-medium text-gray-500">
        New email address
      </label>
      <div className="flex gap-2">
        <input
          type="email"
          value={newEmail}
          onChange={(e) => setNewEmail(e.target.value)}
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <Button type="submit" variant="secondary" disabled={mutation.isPending}>
          {mutation.isPending ? "Sending…" : "Change"}
        </Button>
      </div>
      {serverError && <p className="text-sm text-red-600">{serverError}</p>}
      {mutation.isSuccess && (
        <p className="text-sm text-green-600">
          Check {mutation.data?.pending_email} for a verification link. Your
          current email stays active until you confirm.
        </p>
      )}
    </form>
  );
}

function ExportDataButton() {
  const mutation = useMutation({
    mutationFn: exportMyData,
    onSuccess: (data) => {
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "my-data-export.json";
      link.click();
      URL.revokeObjectURL(url);
    },
  });

  return (
    <Button
      variant="secondary"
      disabled={mutation.isPending}
      onClick={() => mutation.mutate()}
    >
      {mutation.isPending ? "Preparing export…" : "Export my data"}
    </Button>
  );
}

function DeleteAccountButton() {
  const { token, logout } = useAuth();
  const navigate = useNavigate();
  const userId = getUserIdFromToken(token);

  const mutation = useMutation({
    mutationFn: () => {
      if (!userId) throw new Error("Not authenticated");
      return deleteMyAccount(userId);
    },
    onSuccess: () => {
      logout();
      navigate("/login");
    },
  });

  return (
    <ConfirmDeleteButton
      onConfirm={() => mutation.mutate()}
      confirmMessage="This permanently deletes your personal data and logs you out everywhere. This cannot be undone."
      disabled={mutation.isPending}
    >
      Delete my account
    </ConfirmDeleteButton>
  );
}

export function PrivacySection() {
  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Privacy & data" />
      <div className="flex flex-col gap-6">
        <ConsentSummary />
        <MarketingConsentToggle />

        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-2">
            Change email
          </h3>
          <ChangeEmailForm />
        </div>

        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-2">
            Your data
          </h3>
          <div className="flex items-center gap-3">
            <ExportDataButton />
            <DeleteAccountButton />
          </div>
        </div>
      </div>
    </section>
  );
}
