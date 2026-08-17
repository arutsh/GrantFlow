import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "@/context/AuthContext";

// Rendered once by DashboardLayout, above TopBar, so it's present on every
// authenticated page. No dismiss control other than Exit — a hideable
// banner is exactly the failure mode ("forgot I was impersonating") this
// exists to prevent, see design.md decision 6.
export function ImpersonationBanner() {
  const { isImpersonating, impersonatedCustomerName, exitImpersonation } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  if (!isImpersonating) return null;

  const handleExit = () => {
    exitImpersonation();
    queryClient.clear();
    navigate("/dashboard");
  };

  return (
    <div className="flex items-center justify-between gap-3 px-4 py-2 bg-amber-500 text-amber-950 text-sm font-medium flex-shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        <ShieldAlert size={18} className="flex-shrink-0" />
        <span className="truncate">
          Impersonating <strong>{impersonatedCustomerName ?? "a customer"}</strong> as a
          superuser — every action is logged.
        </span>
      </div>
      <button
        type="button"
        onClick={handleExit}
        className="flex-shrink-0 px-3 py-1 rounded-lg bg-amber-950 text-white hover:bg-amber-900 transition-colors"
      >
        Exit impersonation
      </button>
    </div>
  );
}
