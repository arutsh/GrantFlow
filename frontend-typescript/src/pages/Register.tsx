import Button from "@/components/ui/Button";
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { registerUser } from "@/api/usersApi";
import { useAuth } from "@/context/AuthContext";
import { Eye, EyeOff, UserPlus } from "lucide-react";

export default function Register() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [consentDataProcessing, setConsentDataProcessing] = useState(false);
  const [consentMarketing, setConsentMarketing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();

  const mutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      registerUser(email, password, consentDataProcessing, consentMarketing),
    onSuccess: (data) => {
      login(
        data.access_token,
        email,
        false,
        data.status,
        data.refresh_token || "",
      );
      // A brand-new account is never email-verified yet — go straight to
      // the confirm-email screen instead of onboarding.
      navigate("/confirm-email");
    },
    onError: (error: any) => {
      setError(error?.response?.data?.detail || "Registration failed. Please try again.");
      console.error("Registration failed", error);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      // Rest of the policy lives server-side (shared/security/password_policy.py).
      setError("Password must be at least 8 characters");
      return;
    }

    if (!consentDataProcessing) {
      setError("You must consent to data processing to create an account");
      return;
    }

    mutation.mutate({ email, password });
  };

  return (
    <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary/10 via-neutral to-secondary/10">
      <form
        onSubmit={handleSubmit}
        className="bg-white p-8 rounded-2xl card-shadow-lg w-full max-w-md"
      >
        {/* Header */}
        <div className="flex items-center justify-center mb-8">
          <div className="p-3 bg-green-50 rounded-lg">
            <UserPlus size={32} className="text-green-600" />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-center text-slate-900 mb-2">
          Create Account
        </h1>
        <p className="text-center text-gray-500 mb-8">Join GrandFlow today</p>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}

        {/* Email Input */}
        <div className="mb-5">
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

        {/* Password Input */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-slate-900 mb-2">
            Password
          </label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              placeholder="Create a password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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

        {/* Confirm Password Input */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-900 mb-2">
            Confirm Password
          </label>
          <div className="relative">
            <input
              type={showConfirmPassword ? "text" : "password"}
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full px-4 py-2 pr-10 border border-gray-300 rounded-lg input-focus bg-white"
              required
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword((v) => !v)}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              {showConfirmPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        {/* Consent */}
        <div className="mb-4 flex items-start gap-2">
          <input
            type="checkbox"
            id="consent-data-processing"
            checked={consentDataProcessing}
            onChange={(e) => setConsentDataProcessing(e.target.checked)}
            className="mt-1 w-4 h-4 rounded border-gray-300 text-slate-800 focus:ring-2 focus:ring-slate-300 cursor-pointer"
            required
          />
          <label
            htmlFor="consent-data-processing"
            className="text-sm text-gray-600 cursor-pointer"
          >
            I consent to my data being processed to provide this service.
            Required to create an account. See our{" "}
            <a href="/legal#privacy" className="underline hover:opacity-70">
              Privacy Policy
            </a>
            .
          </label>
        </div>
        <div className="mb-6 flex items-start gap-2">
          <input
            type="checkbox"
            id="consent-marketing"
            checked={consentMarketing}
            onChange={(e) => setConsentMarketing(e.target.checked)}
            className="mt-1 w-4 h-4 rounded border-gray-300 text-slate-800 focus:ring-2 focus:ring-slate-300 cursor-pointer"
          />
          <label
            htmlFor="consent-marketing"
            className="text-sm text-gray-600 cursor-pointer"
          >
            Send me occasional product updates by email (optional — you can
            change this anytime in Settings).
          </label>
        </div>

        {/* Sign Up Button */}
        <Button
          type="submit"
          variant="primary"
          className="w-full disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          disabled={mutation.isPending}
        >
          {mutation.isPending ? "Creating account..." : "Create Account"}
        </Button>

        {/* Login Link */}
        <p className="text-center text-gray-600 mt-6">
          Already have an account?{" "}
          <a
            href="/login"
            className="text-slate-700 font-semibold hover:text-slate-900 hover:underline"
          >
            Login
          </a>
        </p>
      </form>
    </div>
  );
}
