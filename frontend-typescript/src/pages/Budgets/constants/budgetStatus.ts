// Single source of truth for budget-status display everywhere a status
// renders (pill badges, composition bars, legends) — kept in a plain
// constants file (not a component file) so react-refresh/only-export-components
// stays happy for files that also export a component (e.g. StatusBadge).
export const STATUS_LABELS: Record<string, string> = {
  draft: "Draft",
  ai_draft: "AI Draft",
  confirmed: "Confirmed",
  archived: "Archived",
};

// Fixed categorical order, kept in sync with the dashboard-concepts mockup
// (openspec/changes/budget-report-iteration-2): draft/confirmed/ai_draft/
// archived each get their own hue everywhere a budget status renders.
export const STATUS_ORDER = ["draft", "ai_draft", "confirmed", "archived"];

export const STATUS_STYLES: Record<string, string> = {
  draft: "bg-slate-100 text-slate-600",
  ai_draft: "bg-amber-100 text-amber-700",
  confirmed: "bg-teal-100 text-teal-700",
  archived: "bg-transparent text-gray-500 border border-dashed border-gray-400",
};

// Solid-fill counterpart of STATUS_STYLES's pill tints, for chart-like uses
// (composition bar segments, legend swatches) where a light tint would be
// invisible — same categorical hue per status, just at fill lightness.
export const STATUS_ACCENT: Record<string, string> = {
  draft: "bg-slate-500",
  ai_draft: "bg-amber-500",
  confirmed: "bg-teal-500",
  archived: "bg-gray-400",
};
