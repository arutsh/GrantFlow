import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { forgotPassword } from "@/api/usersApi";
import Button from "@/components/ui/Button";
import { MailCheck, KeyRound } from "lucide-react";

export default function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const mutation = useMutation({
    mutationFn: () => forgotPassword(email),
    // Generic confirmation regardless of outcome — no enumeration signal.
    onSettled: () => setSubmitted(true),
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  if (submitted) {
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
            If an account exists for <strong>{email}</strong>, we sent a link
            to reset your password.
          </p>
          <p className="text-center text-gray-600">
            <a
              href="/login"
              className="text-slate-700 font-semibold hover:text-slate-900 hover:underline"
            >
              Back to login
            </a>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary/10 via-neutral to-secondary/10">
      <form
        onSubmit={handleSubmit}
        className="bg-white p-8 rounded-2xl card-shadow-lg w-full max-w-md"
      >
        <div className="flex items-center justify-center mb-8">
          <div className="p-3 bg-slate-100 rounded-lg">
            <KeyRound size={32} className="text-slate-700" />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-center text-slate-900 mb-2">
          Forgot password?
        </h1>
        <p className="text-center text-gray-500 mb-8">
          Enter your email and we'll send you a link to reset it.
        </p>

        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-900 mb-2">
            Email Address
          </label>
          <input
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg input-focus bg-white"
            required
          />
        </div>

        <Button
          type="submit"
          variant="primary"
          className="w-full disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "Sending..." : "Send reset link"}
        </Button>

        <p className="text-center text-gray-600 mt-6">
          <a
            href="/login"
            className="text-slate-700 font-semibold hover:text-slate-900 hover:underline"
          >
            Back to login
          </a>
        </p>
      </form>
    </div>
  );
}
