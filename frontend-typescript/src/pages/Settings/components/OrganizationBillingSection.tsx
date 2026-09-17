import { SectionHead } from "@/components/ui/SectionHead";

// Proposed section, not wired to a backend: placeholder for a future paid tier (currently BYOK, no platform fee).
export function OrganizationBillingSection() {
  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Billing" />
      <p className="text-sm text-gray-600">
        OpenGrantFlow is bring-your-own-key for AI usage — there&apos;s no platform fee,
        so there&apos;s nothing to bill for yet. A hosted-key subscription tier is a
        possible future addition, not currently planned.
      </p>
    </section>
  );
}
