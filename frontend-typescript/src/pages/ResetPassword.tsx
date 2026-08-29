import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { resetPassword } from "@/api/usersApi";
import Button from "@/components/ui/Button";
import { Eye, EyeOff, XCircle, KeyRound } from "lucide-react";

const TOKEN_ERROR_DETAIL = "Invalid or expired reset token";

export default function ResetPassword() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const email = searchParams.get("email");
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: () => resetPassword(email as string, token as string, newPassword),
    onSuccess: () => {
      navigate("/login", {
        state: { message: "Password reset. Please log in with your new password." },
      });
    },
  });

  const errorDetail = axios.isAxiosError(mutation.error)
    ? mutation.error.response?.data?.detail
    : undefined;
  const tokenInvalid = errorDetail === TOKEN_ERROR_DETAIL;
  const serverError =
    mutation.isError && !tokenInvalid
      ? errorDetail || "Something went wrong. Please try again."
      : null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (newPassword !== confirmPassword) {
      setFormError("Passwords do not match");
      return;
    }

    if (newPassword.length < 8) {
      // Rest of the policy lives server-side (shared/security/password_policy.py).
      setFormError("Password must be at least 8 characters");
      return;
    }

    mutation.mutate();
  };

  if (!token || !email || tokenInvalid) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary/10 via-neutral to-secondary/10">
        <div className="bg-white p-8 rounded-2xl card-shadow-lg w-full max-w-md text-center flex flex-col items-center">
          <XCircle size={32} className="text-red-600" />
          <h1 className="text-2xl font-bold text-slate-900 mt-4 mb-2">
            {!token || !email ? "Invalid link" : "Link expired or already used"}
          </h1>
          <p className="text-gray-500 mb-6">
            {!token || !email
              ? "This reset link is missing its token or email. Please use the link from your reset email."
              : "This reset link is no longer valid. You can request a new one."}
          </p>
          <Link
            to="/forgot-password"
            className="text-slate-700 font-semibold hover:text-slate-900 hover:underline"
          >
            Request a new reset link
          </Link>
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
          Reset your password
        </h1>
        <p className="text-center text-gray-500 mb-8">
          Choose a new password for <strong>{email}</strong>.
        </p>

        {(formError || serverError) && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{formError || serverError}</p>
          </div>
        )}

        <div className="mb-5">
          <label className="block text-sm font-medium text-slate-900 mb-2">
            New Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Enter a new password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg input-focus bg-white"
              required
            />
            <button
              type="button"
              onClick={() => setShowPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-1">
            At least 8 characters, not entirely numeric
          </p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-900 mb-2">
            Confirm New Password
          </label>
          <input
            type={showPassword ? "text" : "password"}
            placeholder="Confirm your new password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
          {mutation.isPending ? "Resetting..." : "Reset password"}
        </Button>
      </form>
    </div>
  );
}
