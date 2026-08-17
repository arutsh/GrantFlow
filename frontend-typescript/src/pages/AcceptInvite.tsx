import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import axios from "axios";
import { acceptInvite } from "@/api/adminManagementApi";
import Button from "@/components/ui/Button";
import PasswordInput from "@/components/ui/PasswordInput";
import { XCircle } from "lucide-react";

export default function AcceptInvite() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const email = searchParams.get("email");
  const navigate = useNavigate();
  const [password, setPassword] = useState("");

  const mutation = useMutation({
    mutationFn: () => acceptInvite(email as string, token as string, password),
    onSuccess: () => navigate("/login"),
  });

  // FastAPI returns a plain string `detail` for HTTPException (e.g. an
  // expired token) but a list of {msg, ...} objects for pydantic validation
  // errors like a weak password — surface either as readable text.
  const errorMessage = (() => {
    if (!axios.isAxiosError(mutation.error)) {
      return "This invitation link is invalid or has expired.";
    }
    const detail = mutation.error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail) && typeof detail[0]?.msg === "string") return detail[0].msg;
    return "This invitation link is invalid or has expired.";
  })();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate();
  };

  if (!token || !email) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary/10 via-neutral to-secondary/10">
        <div className="bg-white p-8 rounded-2xl card-shadow-lg w-full max-w-md text-center flex flex-col items-center">
          <XCircle size={32} className="text-red-600" />
          <h1 className="text-2xl font-bold text-slate-900 mt-4 mb-2">Invalid link</h1>
          <p className="text-gray-500 mb-6">
            This invitation link is missing its token or email. Please use the link
            from your invite email.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary/10 via-neutral to-secondary/10">
      <div className="bg-white p-8 rounded-2xl card-shadow-lg w-full max-w-md text-center flex flex-col items-center">
        <h1 className="text-2xl font-bold text-slate-900 mb-2">Accept your invite</h1>
        <p className="text-gray-500 mb-6">
          Set a password for <span className="font-medium">{email}</span> to finish
          joining your team.
        </p>

        <form onSubmit={handleSubmit} className="w-full text-left">
          <PasswordInput
            label="Password"
            name="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <Button
            type="submit"
            variant="primary"
            className="w-full font-medium"
            disabled={mutation.isPending}
          >
            Set password and continue
          </Button>
        </form>

        {mutation.isError && (
          <p className="text-sm text-red-500 mt-4">
            {errorMessage}{" "}
            <Link to="/login" className="underline">
              Go to login
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
