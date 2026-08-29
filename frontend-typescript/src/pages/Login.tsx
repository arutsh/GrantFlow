import { useEffect, useState } from "react";
import { STATUS, useAuth } from "@/context/AuthContext";
import { loginUser } from "@/api/usersApi";
import { useLocation, useNavigate } from "react-router-dom";
import Button from "@/components/ui/Button";
import { LogIn } from "lucide-react";

export default function Login() {
  const { isAuthenticated, isRegistering, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [remember, setRemember] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const successMessage = (location.state as { message?: string } | null)?.message;

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    try {
      const res = await loginUser(username, password);
      login(
        res.access_token,
        username,
        remember,
        res.status,
        res.refresh_token,
      );
      if (res.status === STATUS.PENDING) {
        navigate("/onboarding");
      } else {
        navigate("/dashboard");
      }
    } catch (err: any) {
      const status = err?.response?.status;
      const detail = err?.response?.data?.detail;
      if (status === 403 && detail === "email_not_verified") {
        // Valid credentials, but no session — route to confirm-email.
        navigate("/confirm-email", { state: { email: username } });
      } else if (status === 429) {
        setError(detail || "Too many failed login attempts. Try again later.");
      } else if (status === 401) {
        setError("Invalid username or password");
      } else {
        setError(detail || "Something went wrong. Please try again.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen items-center justify-center bg-gradient-to-br from-primary/10 via-neutral to-secondary/10">
      <form
        onSubmit={handleLogin}
        className="bg-white p-8 rounded-2xl card-shadow-lg w-full max-w-md"
      >
        {/* Header */}
        <div className="flex items-center justify-center mb-8">
          <div className="p-3 bg-slate-100 rounded-lg">
            <LogIn size={32} className="text-slate-700" />
          </div>
        </div>

        <h1 className="text-3xl font-bold text-center text-slate-900 mb-2">
          GrandFlow
        </h1>
        <p className="text-center text-gray-500 mb-8">Welcome back</p>

        {/* Success Message */}
        {!error && successMessage && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-green-700 text-sm">{successMessage}</p>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-600 text-sm">{error}</p>
          </div>
        )}

        {/* Username Input */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-slate-900 mb-2">
            Username
          </label>
          <input
            type="text"
            placeholder="Enter your username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg input-focus bg-white"
            required
          />
        </div>

        {/* Password Input */}
        <div className="mb-6">
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium text-slate-900">
              Password
            </label>
            <a
              href="/forgot-password"
              className="text-sm text-slate-700 font-medium hover:text-slate-900 hover:underline"
            >
              Forgot password?
            </a>
          </div>
          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg input-focus bg-white"
            required
          />
        </div>

        {/* Remember Me */}
        <div className="flex items-center mb-6">
          <input
            type="checkbox"
            id="remember"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
            className="w-4 h-4 rounded border-gray-300 text-slate-800 focus:ring-2 focus:ring-slate-300 cursor-pointer"
          />
          <label
            htmlFor="remember"
            className="ml-2 text-sm text-gray-600 cursor-pointer"
          >
            Remember me
          </label>
        </div>

        {/* Login Button */}
        <Button
          type="submit"
          variant="primary"
          className="w-full disabled:opacity-50 disabled:cursor-not-allowed font-medium"
          disabled={isLoading}
        >
          {isLoading ? "Logging in..." : "Login"}
        </Button>

        {/* Sign Up Link */}
        <p className="text-center text-gray-600 mt-6">
          Don't have an account?{" "}
          <a
            href="/register"
            className="text-slate-700 font-semibold hover:text-slate-900 hover:underline"
          >
            Sign up
          </a>
        </p>
      </form>
    </div>
  );
}
