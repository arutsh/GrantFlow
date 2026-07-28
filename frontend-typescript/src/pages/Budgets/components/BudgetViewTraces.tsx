import { Card, CardContent, CardHeader } from "@/components/ui/Card";

function TraceBlock({ label, event }: { label: string; event?: { user?: { first_name?: string; last_name?: string; email?: string } | null; event_date?: string | null } | null }) {
  const name = [event?.user?.first_name, event?.user?.last_name].filter(Boolean).join(" ") || "—";
  return (
    <div className="p-4 bg-slate-50 rounded-lg border border-slate-200">
      <h3 className="text-micro-label mb-2">
        {label}
      </h3>
      <p className="text-sm font-medium text-slate-700">{name}</p>
      <p className="text-sm text-slate-500">{event?.user?.email ?? "—"}</p>
      <p className="text-xs text-slate-400 mt-1">
        {event?.event_date ? new Date(event.event_date).toLocaleString() : "—"}
      </p>
    </div>
  );
}

export function BudgetViewTraces({ budget }: { budget: any }) {
  return (
    <Card className="grid md:grid-cols-2 gap-4 p-6 bg-white rounded-xl border border-slate-200 shadow-sm">
      <CardHeader className="contents">
        <TraceBlock label="Created" event={budget.trace?.created} />
      </CardHeader>
      <CardContent className="contents">
        <TraceBlock label="Last Updated" event={budget.trace?.updated} />
      </CardContent>
    </Card>
  );
}
