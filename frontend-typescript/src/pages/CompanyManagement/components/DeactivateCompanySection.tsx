import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { SectionHead } from "@/components/ui/SectionHead";
import { ConfirmDeleteButton } from "@/components/ui/Button";
import { useAuth } from "@/context/AuthContext";
import { deactivateCustomer } from "@/api/customerApi";

// Company deactivation is the one action in this feature that a plain
// company admin can never take on their own company — only a superuser,
// direct or mid-impersonation (design.md decision 2). This section only
// renders while impersonating, so exiting afterward is the natural next
// step rather than staying "logged in" as a now-deactivated company.
export function DeactivateCompanySection({ customerId }: { customerId: string }) {
  const { exitImpersonation } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const deactivateMutation = useMutation({
    mutationFn: () => deactivateCustomer(customerId),
    onSuccess: () => {
      exitImpersonation();
      queryClient.clear();
      navigate("/dashboard");
    },
  });

  return (
    <section className="bg-white rounded-xl border border-red-200 p-6">
      <SectionHead title="Danger zone" />
      <p className="text-sm text-slate-500 mb-4">
        Deactivating this company blocks its users from logging in. This does not
        delete any data.
      </p>
      <ConfirmDeleteButton
        onConfirm={() => deactivateMutation.mutate()}
        disabled={deactivateMutation.isPending}
        confirmMessage="Deactivate this company?"
      >
        Deactivate company
      </ConfirmDeleteButton>
      {deactivateMutation.isError && (
        <p className="text-xs text-red-500 mt-3">Failed to deactivate this company.</p>
      )}
    </section>
  );
}
