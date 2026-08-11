import { SectionHead } from "@/components/ui/SectionHead";

// Proposed section, not wired to a backend: every email GrandFlow sends
// today (verification, receipts) is transactional/mandatory, so there's no
// preference to store yet. Placeholder for when opt-in notifications exist.
const STUB_PREFERENCES = [
  {
    label: "Budget approval needed",
    hint: "When a report you submitted needs sign-off.",
  },
  {
    label: "Weekly digest",
    hint: "Summary of activity across your organization.",
  },
];

export function NotificationsSection() {
  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Notifications" />
      <div className="flex flex-col gap-4">
        {STUB_PREFERENCES.map((pref) => (
          <div
            key={pref.label}
            className="flex items-center justify-between max-w-md opacity-50"
          >
            <div>
              <p className="text-sm font-medium text-gray-900">{pref.label}</p>
              <p className="text-xs text-gray-500">{pref.hint}</p>
            </div>
            <input type="checkbox" disabled className="h-4 w-4" />
          </div>
        ))}
        <p className="text-xs text-gray-500">
          Not built yet — shown here to reserve the slot in the nav rather than
          reshuffle it later.
        </p>
      </div>
    </section>
  );
}
