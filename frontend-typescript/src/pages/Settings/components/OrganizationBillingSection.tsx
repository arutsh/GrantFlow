import { SectionHead } from "@/components/ui/SectionHead";

// Proposed section, not wired to a backend: GrandFlow is BYOK for AI usage
// today (see AI & integrations), so there's no platform fee to bill for.
// Placeholder so a future paid tier has a slot without reshuffling the nav.
export function OrganizationBillingSection() {
  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Billing" />
      <p className="text-sm text-gray-600">
        GrandFlow is bring-your-own-key for AI usage — there&apos;s no platform fee,
        so there&apos;s nothing to bill for yet. A hosted-key subscription tier is a
        possible future addition, not currently planned.
      </p>
    </section>
  );
}
