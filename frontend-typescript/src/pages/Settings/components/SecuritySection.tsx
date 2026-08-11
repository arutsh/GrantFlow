import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionHead } from "@/components/ui/SectionHead";
import Button from "@/components/ui/Button";
import {
  changePassword,
  listSessions,
  revokeSession,
} from "@/api/usersApi";

function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function ChangePasswordForm() {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => changePassword(currentPassword, newPassword),
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setLocalError(null);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (newPassword !== confirmPassword) {
      setLocalError("New passwords do not match");
      return;
    }
    if (newPassword.length < 8) {
      // Rest of the policy lives server-side (shared/security/password_policy.py).
      setLocalError("Password must be at least 8 characters");
      return;
    }
    mutation.mutate();
  };

  const serverError =
    (mutation.error as { response?: { data?: { detail?: string } } })
      ?.response?.data?.detail;

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 max-w-sm">
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          Current password
        </label>
        <input
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          New password
        </label>
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
        <p className="text-xs text-gray-500 mt-1">At least 8 characters</p>
      </div>
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">
          Confirm new password
        </label>
        <input
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          required
        />
      </div>

      {(localError || serverError) && (
        <p className="text-sm text-red-600">{localError || serverError}</p>
      )}
      {mutation.isSuccess && (
        <p className="text-sm text-green-600">Password updated.</p>
      )}

      <Button
        type="submit"
        variant="primary"
        disabled={mutation.isPending}
        className="self-start"
      >
        {mutation.isPending ? "Updating…" : "Update password"}
      </Button>
    </form>
  );
}

function ActiveSessions() {
  const queryClient = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["auth-sessions"],
    queryFn: listSessions,
  });

  const revokeMutation = useMutation({
    mutationFn: (sessionId: string) => revokeSession(sessionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["auth-sessions"] });
    },
  });

  if (isLoading) return <p className="text-sm text-gray-400">Loading…</p>;

  return (
    <div className="flex flex-col gap-2">
      {data?.length === 0 && (
        <p className="text-sm text-gray-500">No active sessions.</p>
      )}
      {data?.map((session) => (
        <div
          key={session.id}
          className="flex items-center justify-between border border-gray-200 rounded-lg px-4 py-3"
        >
          <div>
            <p className="text-sm font-medium text-gray-900">
              {session.current ? "This device" : "Other device"}
            </p>
            <p className="text-xs text-gray-500">
              Signed in {formatDate(session.issued_at)} · expires{" "}
              {formatDate(session.expires_at)}
            </p>
          </div>
          {!session.current && (
            <Button
              variant="danger"
              className="text-xs py-1 px-2"
              disabled={revokeMutation.isPending}
              onClick={() => revokeMutation.mutate(session.id)}
            >
              Revoke
            </Button>
          )}
        </div>
      ))}
    </div>
  );
}

export function SecuritySection() {
  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Security" />
      <div className="flex flex-col gap-6">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Change password
          </h3>
          <ChangePasswordForm />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-gray-900 mb-3">
            Active sessions
          </h3>
          <ActiveSessions />
        </div>
      </div>
    </section>
  );
}
