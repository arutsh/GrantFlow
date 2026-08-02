type TraceEvent = {
  user?: { first_name?: string; last_name?: string; email?: string } | null;
  event_date?: string | null;
} | null;

function traceText(label: string, event: TraceEvent): string {
  const name = [event?.user?.first_name, event?.user?.last_name].filter(Boolean).join(" ") || "—";
  const date = event?.event_date ? new Date(event.event_date).toLocaleString() : "—";
  return `${label} by ${name} · ${date}`;
}

// Provenance metadata — the least important thing on this page, so it gets
// one slim caption line rather than two full padded cards (see
// budget-view-redesign proposal, note 7).
export function BudgetViewTraces({ budget }: { budget: any }) {
  return (
    <div className="px-1 text-xs text-slate-400 flex flex-wrap items-center gap-x-1.5 gap-y-0.5">
      <span>{traceText("Created", budget.trace?.created)}</span>
      <span className="text-slate-300">—</span>
      <span>{traceText("Updated", budget.trace?.updated)}</span>
    </div>
  );
}
