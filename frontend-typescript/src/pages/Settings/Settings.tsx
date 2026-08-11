import { useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { SettingsNav, type SettingsSectionKey } from "./components/SettingsNav";
import { ProfileSection } from "./components/ProfileSection";
import { SecuritySection } from "./components/SecuritySection";
import { PrivacySection } from "./components/PrivacySection";
import { NotificationsSection } from "./components/NotificationsSection";
import { OrganizationGeneralSection } from "./components/OrganizationGeneralSection";
import { ManageGrantees } from "./components/ManageGrantees";
import { AiIntegrationsSection } from "./components/AiIntegrationsSection";
import { OrganizationBillingSection } from "./components/OrganizationBillingSection";

export default function SettingsPage() {
  const { isDonor } = useAuth();
  const [section, setSection] = useState<SettingsSectionKey>("profile");

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-semibold text-gray-900 mb-8">Account Settings</h1>

      <div className="flex flex-col md:flex-row gap-6 items-start">
        <SettingsNav active={section} onChange={setSection} showGrantees={isDonor} />

        <div className="flex-1 min-w-0 w-full flex flex-col gap-4">
          {section === "profile" && <ProfileSection />}
          {section === "security" && <SecuritySection />}
          {section === "privacy" && <PrivacySection />}
          {section === "notifications" && <NotificationsSection />}
          {section === "org-general" && <OrganizationGeneralSection />}
          {section === "org-members" && isDonor && <ManageGrantees />}
          {section === "org-ai" && <AiIntegrationsSection />}
          {section === "org-billing" && <OrganizationBillingSection />}
        </div>
      </div>
    </div>
  );
}
