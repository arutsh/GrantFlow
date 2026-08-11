export type SettingsSectionKey =
  | "profile"
  | "security"
  | "privacy"
  | "notifications"
  | "org-general"
  | "org-members"
  | "org-ai"
  | "org-billing";

interface NavItem {
  key: SettingsSectionKey;
  label: string;
}

// Grouped along the User/Customer split that already exists in the data
// model: "My account" is this person's own data, "Organization" belongs to
// the customer record and is shared by every teammate on it.
const MY_ACCOUNT_ITEMS: NavItem[] = [
  { key: "profile", label: "Profile" },
  { key: "security", label: "Security" },
  { key: "privacy", label: "Privacy & data" },
  { key: "notifications", label: "Notifications" },
];

const ORG_ITEMS: NavItem[] = [
  { key: "org-general", label: "General" },
  { key: "org-members", label: "Members & grantees" },
  { key: "org-ai", label: "AI & integrations" },
  { key: "org-billing", label: "Billing" },
];

function NavGroup({
  label,
  items,
  active,
  onChange,
}: {
  label: string;
  items: NavItem[];
  active: SettingsSectionKey;
  onChange: (key: SettingsSectionKey) => void;
}) {
  return (
    <div className="flex md:flex-col gap-1 flex-shrink-0">
      <span className="hidden md:block text-xs font-semibold uppercase tracking-wide text-gray-400 px-3 mb-1">
        {label}
      </span>
      {items.map((item) => (
        <button
          key={item.key}
          type="button"
          onClick={() => onChange(item.key)}
          aria-current={active === item.key ? "page" : undefined}
          className={`text-left px-3 py-2 rounded-lg text-sm whitespace-nowrap transition-colors ${
            active === item.key
              ? "bg-slate-700 text-white font-medium"
              : "text-gray-600 hover:bg-gray-100"
          }`}
        >
          {item.label}
        </button>
      ))}
    </div>
  );
}

export function SettingsNav({
  active,
  onChange,
  showGrantees,
}: {
  active: SettingsSectionKey;
  onChange: (key: SettingsSectionKey) => void;
  showGrantees: boolean;
}) {
  // Grantee management is donor-only (approving/revoking grantee orgs) —
  // matches the gating the old flat Settings page applied to ManageGrantees.
  const orgItems = ORG_ITEMS.filter((item) => item.key !== "org-members" || showGrantees);

  return (
    <nav
      aria-label="Settings sections"
      className="flex md:flex-col gap-4 md:gap-6 overflow-x-auto md:overflow-visible w-full min-w-0 md:w-48 flex-shrink-0 pb-1 md:pb-0"
    >
      <NavGroup label="My account" items={MY_ACCOUNT_ITEMS} active={active} onChange={onChange} />
      <NavGroup label="Organization" items={orgItems} active={active} onChange={onChange} />
    </nav>
  );
}
