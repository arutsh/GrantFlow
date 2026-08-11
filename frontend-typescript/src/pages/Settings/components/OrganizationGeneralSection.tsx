import { SectionHead } from "@/components/ui/SectionHead";

// Proposed section, not wired to a backend: the Customer record has no
// self-service edit surface yet, and who's allowed to edit it (role model)
// isn't decided. Placeholder for when that ships.
const FIELDS = ["Organization name", "Country", "Registration / tax ID", "Website"];

export function OrganizationGeneralSection() {
  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Organization" />
      <div className="flex flex-col gap-4 max-w-sm">
        {FIELDS.map((label) => (
          <div key={label}>
            <label className="block text-xs font-medium text-gray-500 mb-1">
              {label}
            </label>
            <input
              type="text"
              placeholder="Not available yet"
              disabled
              className="w-full border border-gray-200 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-400"
            />
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
