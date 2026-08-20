import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { verifyEmail } from "@/api/usersApi";
import { useAuth } from "@/context/AuthContext";
import Button from "@/components/ui/Button";
import { CheckCircle2, XCircle } from "lucide-react";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");
  const email = searchParams.get("email");
  const navigate = useNavigate();
  const { login, isAuthenticated } = useAuth();

  const mutation = useMutation({
    mutationFn: () => verifyEmail(email as string, token as string),
    onSuccess: (data) => {
      // Verification is the account's first session.
      login(data.access_token, email || "", false, data.status, data.refresh_token || "");
    },
  });

  useEffect(() => {
    if (token && email) {
      mutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, email]);

  const handleContinue = () => {
    navigate(isAuthenticated ? "/onboarding" : "/login");
  };

  let body: React.ReactNode;
  if (!token || !email) {
    body = (
      <>
        <XCircle size={32} className="text-red-600" />
        <h1 className="text-2xl font-bold text-slate-900 mt-4 mb-2">
          Invalid link
        </h1>
        <p className="text-gray-500 mb-6">
          This verification link is missing its token or email. Please use
          the link from your confirmation email.
        </p>
      </>
    );
  } else if (mutation.isPending || mutation.isIdle) {
    body = <p className="text-gray-500">Confirming your email…</p>;
  } else if (mutation.isSuccess) {
    body = (
      <>
        <CheckCircle2 size={32} className="text-green-600" />
        <h1 className="text-2xl font-bold text-slate-900 mt-4 mb-2">
          Email confirmed
        </h1>
        <p className="text-gray-500 mb-6">
          Your email address has been verified.
        </p>
        <Button
          type="button"
          variant="primary"
          className="w-full font-medium"
          onClick={handleContinue}
        >
          Continue
        </Button>
      </>
    );
  } else {
    body = (
      <>
        <XCircle size={32} className="text-red-600" />
        <h1 className="text-2xl font-bold text-slate-900 mt-4 mb-2">
          Link expired or already used
        </h1>
        <p className="text-gray-500 mb-6">
          This verification link is no longer valid. You can request a new
          one from the confirm-email screen.
        </p>
        <Link
          to="/confirm-email"
          className="text-slate-700 font-semibold hover:text-slate-900 hover:underline"
        >
          Resend confirmation email
        </Link>
      </>
    );
  }

  return (
    <div className="flex items-center justify-center h-screen bg-gradient-to-br from-primary/10 via-neutral to-secondary/10">
      <div className="bg-white p-8 rounded-2xl card-shadow-lg w-full max-w-md text-center flex flex-col items-center">
        {body}
      </div>
    </div>
  );
}
