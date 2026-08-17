import { useAuth } from "@/context/AuthContext";
import { getCurrentCustomerId } from "@/utils/roleAccess";
import { CompanyPicker } from "@/pages/CompanyManagement/components/CompanyPicker";
import { CompanyDetailsForm } from "@/pages/CompanyManagement/components/CompanyDetailsForm";
import { DeactivateCompanySection } from "@/pages/CompanyManagement/components/DeactivateCompanySection";

// Picking a company (superuser only) starts an impersonation session.
export function OrganizationGeneralSection() {
  const { isSuperuser, isImpersonating } = useAuth();

  if (isSuperuser && !isImpersonating) {
    return <CompanyPicker />;
  }

  const customerId = getCurrentCustomerId();
  if (!customerId) return null;

  return (
    <div className="flex flex-col gap-4">
      <CompanyDetailsForm customerId={customerId} />
      {isImpersonating && <DeactivateCompanySection customerId={customerId} />}
    </div>
  );
}
