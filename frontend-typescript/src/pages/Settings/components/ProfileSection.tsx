import { SectionHead } from "@/components/ui/SectionHead";
import { useAuth } from "@/context/AuthContext";

// Proposed section, not wired to a backend: there's no profile-edit endpoint
// (name, photo) yet, and duplicating the change-email flow here would fork
// it from the one on Privacy & data. Read-only until that's designed.
export function ProfileSection() {
  const { username } = useAuth();

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Profile" />
      <div className="flex flex-col gap-4 max-w-sm">
        <div>
          <label className="block text-xs font-medium text-gray-500 mb-1">
            Email address
          </label>
          <input
            type="email"
            value={username ?? ""}
            disabled
            className="w-full border border-gray-200 bg-gray-50 rounded-lg px-3 py-2 text-sm text-gray-600"
          />
        </div>
        <p className="text-xs text-gray-500">
          Name and photo aren&apos;t collected yet, so there&apos;s nothing editable here
          beyond your email. To change it, use Privacy &amp; data.
        </p>
      </div>
    </section>
  );
}
