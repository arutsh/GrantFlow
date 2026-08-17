import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { acceptInvite } from "@/api/adminManagementApi";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
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
          <Input
            label="Password"
            name="password"
            type="password"
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
            This invitation link is invalid or has expired.{" "}
            <Link to="/login" className="underline">
              Go to login
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
