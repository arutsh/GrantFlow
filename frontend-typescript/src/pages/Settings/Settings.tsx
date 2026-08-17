import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { SettingsNav, type SettingsSectionKey } from "./components/SettingsNav";
import { ProfileSection } from "./components/ProfileSection";
import { SecuritySection } from "./components/SecuritySection";
import { PrivacySection } from "./components/PrivacySection";
import { NotificationsSection } from "./components/NotificationsSection";
import { OrganizationGeneralSection } from "./components/OrganizationGeneralSection";
import { TeamSection } from "./components/TeamSection";
import { ManageGrantees } from "./components/ManageGrantees";
import { AiIntegrationsSection } from "./components/AiIntegrationsSection";
import { OrganizationBillingSection } from "./components/OrganizationBillingSection";

export default function SettingsPage() {
  const { isDonor, isAdmin, isSuperuser, isImpersonating } = useAuth();
  const [section, setSection] = useState<SettingsSectionKey>("profile");

  const showCompanyGeneral = isAdmin || isSuperuser;
  const showTeam = isAdmin || (isSuperuser && isImpersonating);

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold text-gray-900 mb-8">Account Settings</h1>

      <div className="flex flex-col md:flex-row gap-6 items-start">
        <SettingsNav
          active={section}
          onChange={setSection}
          showGrantees={isDonor}
          showCompanyGeneral={showCompanyGeneral}
          showTeam={showTeam}
        />

        <div className="flex-1 min-w-0 w-full flex flex-col gap-4">
          {section === "profile" && <ProfileSection />}
          {section === "security" && <SecuritySection />}
          {section === "privacy" && <PrivacySection />}
          {section === "notifications" && <NotificationsSection />}
          {section === "org-general" && showCompanyGeneral && <OrganizationGeneralSection />}
          {section === "org-team" && showTeam && <TeamSection />}
          {section === "org-members" && isDonor && <ManageGrantees />}
          {section === "org-ai" && <AiIntegrationsSection />}
          {section === "org-billing" && <OrganizationBillingSection />}
        </div>
      </div>
    </div>
  );
}
