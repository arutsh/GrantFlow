// Small uppercase section label + optional right-aligned hint, e.g.
// "GRANTEES" / "5 organisations funded". Replaces the ad hoc
// `<h2 className="text-2xl font-bold text-slate-900 mb-4">` heading
// repeated across DonorDashboard/Dashboard/etc. — one shared component so
// every dashboard-style page's section rhythm stays in sync.
export function SectionHead({ title, hint }: { title: string; hint?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-3 mb-4">
      <h2 className="text-section-title">{title}</h2>
      {hint && <span className="text-xs text-slate-400">{hint}</span>}
    </div>
  );
}
