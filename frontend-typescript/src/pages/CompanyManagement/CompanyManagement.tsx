import { Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { getCurrentCustomerId } from "@/utils/roleAccess";
import { CompanyPicker } from "./components/CompanyPicker";
import { CompanyDetailsForm } from "./components/CompanyDetailsForm";
import { TeamMembers } from "./components/TeamMembers";
import { DeactivateCompanySection } from "./components/DeactivateCompanySection";

// Admin-only page (design.md's two capabilities: company-user-administration
// for a company's own admin, superuser-tenant-administration for a
// superuser). A superuser reaches the same admin view by impersonating a
// company first — no separate superuser UI exists beyond the picker below,
// per design.md decision 2.
export default function CompanyManagementPage() {
  const { isAdmin, isSuperuser, isImpersonating } = useAuth();

  if (isSuperuser && !isImpersonating) {
    return (
      <div className="max-w-4xl">
        <h1 className="text-2xl font-semibold text-gray-900 mb-8">Company Management</h1>
        <CompanyPicker />
      </div>
    );
  }

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  const customerId = getCurrentCustomerId();
  if (!customerId) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <div className="max-w-4xl flex flex-col gap-6">
      <h1 className="text-2xl font-semibold text-gray-900">Company Management</h1>
      <CompanyDetailsForm customerId={customerId} />
      <TeamMembers />
      {isImpersonating && <DeactivateCompanySection customerId={customerId} />}
    </div>
  );
}
