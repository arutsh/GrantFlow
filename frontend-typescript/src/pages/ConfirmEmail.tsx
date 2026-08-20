import { useState } from "react";
import { useLocation } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { resendVerification } from "@/api/usersApi";
import { useAuth } from "@/context/AuthContext";
import Button from "@/components/ui/Button";
import { MailCheck } from "lucide-react";

export default function ConfirmEmail() {
  // Reachable unauthenticated now, so prefer the email passed via navigation.
  const location = useLocation();
  const { username, isAuthenticated, logout } = useAuth();
  const email = (location.state as { email?: string } | null)?.email || username;
  const [justSent, setJustSent] = useState(false);

  const mutation = useMutation({
    mutationFn: () => resendVerification(email as string),
    onSuccess: () => setJustSent(true),
  });

  return (
    <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary/10 via-neutral to-secondary/10">
      <div className="bg-white p-8 rounded-2xl card-shadow-lg w-full max-w-md text-center">
        <div className="flex items-center justify-center mb-8">
          <div className="p-3 bg-green-50 rounded-lg">
            <MailCheck size={32} className="text-green-600" />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-slate-900 mb-2">
          Check your email
        </h1>
        <p className="text-gray-500 mb-8">
          We sent a confirmation link to{" "}
          {email ? <strong>{email}</strong> : "your email address"}.
          Click it to finish setting up your account.
        </p>

        {mutation.isError && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">
              Couldn't resend the email. Please try again.
            </p>
          </div>
        )}

        <Button
          type="button"
          variant="primary"
          className="w-full disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          disabled={!email || mutation.isPending || justSent}
          onClick={() => mutation.mutate()}
        >
          {justSent
            ? "Email sent"
            : mutation.isPending
              ? "Sending..."
              : "Resend confirmation email"}
        </Button>

        {isAuthenticated ? (
          <p className="text-center text-gray-600 mt-6">
            Wrong account?{" "}
            <button
              type="button"
              onClick={logout}
              className="text-slate-700 font-semibold hover:text-slate-900 hover:underline"
            >
              Log out
            </button>
          </p>
        ) : (
          <p className="text-center text-gray-600 mt-6">
            Wrong account?{" "}
            <a
              href="/register"
              className="text-slate-700 font-semibold hover:text-slate-900 hover:underline"
            >
              Register again
            </a>
          </p>
        )}
      </div>
    </div>
  );
}
