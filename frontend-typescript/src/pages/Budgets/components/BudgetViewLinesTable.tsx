import { TableCommon } from "@/components/ui/Table";
import { ColumnDef, createColumnHelper } from "@tanstack/react-table";
import { useMemo, useState } from "react";
import { BudgetLine, NewBudgetLine } from "../types/budget";
import Button, { ConfirmDeleteButton } from "@/components/ui/Button";
import { deleteBudgetLine } from "@/api/gatewayApi";
import { useMutation } from "@tanstack/react-query";
import { useDetailedBudget } from "../SingleBudgetViewContext";
import { formatCurrency } from "@/utils/currency";
import { Edit2, Trash2 } from "lucide-react";
const columnHelper = createColumnHelper<any>();

const USED_TONE_CLASSES: Record<
  "good" | "warn" | "danger" | "neutral",
  string
> = {
  good: "bg-green-100 text-green-700",
  warn: "bg-amber-100 text-amber-700",
  danger: "bg-red-100 text-red-700",
  neutral: "bg-slate-100 text-slate-500",
};

// Local UI state only — not persisted, same footprint as any other
// client-side view toggle (design.md Decision 6).
type CurrencyDisplayMode = "local" | "donor" | "both";

// estimated_exchange_rate is actual_currency -> local_currency (e.g. 0.8
// means 1 EUR ~= 0.8 GBP), so converting a local figure back to the donor's
// currency divides by the rate. Purely a display-layer estimate, never a
// stored per-line amount (design.md Decision 5).
function toDonorAmount(localAmount: number, rate: number): number {
  return localAmount / rate;
}

function AmountDisplay({
  localAmount,
  mode,
  localCurrency,
  actualCurrency,
  rate,
  // "(est.)" belongs on the column header wherever a column already states
  // a single currency unambiguously (desktop table); only a cell that must
  // convey two currencies at once (a combined "both" cell, or a mobile card
  // with no persistent header) still needs it repeated inline.
  labelInline = true,
}: {
  localAmount: number;
  mode: CurrencyDisplayMode;
  localCurrency: string | undefined;
  actualCurrency: string | undefined;
  rate: number | null | undefined;
  labelInline?: boolean;
}) {
  if (mode === "local" || !rate) {
    return <>{formatCurrency(localAmount, localCurrency)}</>;
  }
  const donorAmount = toDonorAmount(localAmount, rate);
  const donorText = labelInline
    ? `${formatCurrency(donorAmount, actualCurrency)} (est.)`
    : formatCurrency(donorAmount, actualCurrency);
  if (mode === "donor") return <>{donorText}</>;
  return (
    <>
      {formatCurrency(localAmount, localCurrency)}
      <span className="text-slate-400"> / </span>
      {donorText}
    </>
  );
}

// Compact-pill treatment for "how much of this budget line has been
// reported so far" — option B from the spend-tracking mockup
// (https://claude.ai/code/artifact/85bd0992-2081-4335-a9d2-48cfe41ec61c),
// picked over an inline progress bar and a separate spending panel.
function UsedPill({
  used,
  allocated,
  currency,
  displayMode,
  actualCurrency,
  rate,
  labelInline = true,
  loading = false,
}: {
  used: number;
  allocated: number;
  currency: string | undefined;
  displayMode: CurrencyDisplayMode;
  actualCurrency: string | undefined;
  rate: number | null | undefined;
  labelInline?: boolean;
  loading?: boolean;
}) {
  // Avoid a real-looking "0%" while spend is still loading (#216).
  if (loading) {
    return (
      <div>
        <span
          className={`inline-flex items-center text-xs font-bold px-2.5 py-0.5 rounded-full animate-pulse ${USED_TONE_CLASSES.neutral}`}
        >
          …
        </span>
        <div className="text-xs text-slate-400 mt-1">Loading…</div>
      </div>
    );
  }

  const pct = allocated > 0 ? Math.round((used / allocated) * 100) : null;
  const tone: "good" | "warn" | "danger" | "neutral" =
    pct === null || pct > 100
      ? "danger"
      : pct === 100
        ? "good"
        : pct > 0
          ? "warn"
          : "neutral";

  return (
    <div>
      <span
        className={`inline-flex items-center text-xs font-bold px-2.5 py-0.5 rounded-full ${USED_TONE_CLASSES[tone]}`}
      >
        {pct === null ? "—" : `${pct}%`}
      </span>
      <div className="text-xs text-slate-400 mt-1">
        <AmountDisplay
          localAmount={used}
          mode={displayMode}
          localCurrency={currency}
          actualCurrency={actualCurrency}
          rate={rate}
          labelInline={labelInline}
        />{" "}
        /{" "}
        <AmountDisplay
          localAmount={allocated}
          mode={displayMode}
          localCurrency={currency}
          actualCurrency={actualCurrency}
          rate={rate}
          labelInline={labelInline}
        />
      </div>
    </div>
  );
}

export function BudgetViewLinesTable({
  lines,
  onEdit,
  // onDelete,
  onNew,
  onClose,
  readOnly = false,
}: {
  lines: BudgetLine[] | undefined;
  onEdit: (BudgetLine: any) => void;
  // onDelete: (budget_id: string) => void;
  onNew: () => void;
  onClose: () => void;
  readOnly?: boolean;
}) {
  const { budget, setBudget, spendByLineId, isSpendPending } =
    useDetailedBudget();
  const [displayMode, setDisplayMode] = useState<CurrencyDisplayMode>("local");
  const rate = budget?.estimated_exchange_rate;
  // A rate of exactly 0 is meaningless (division by zero downstream in
  // toDonorAmount) — treat it the same as "no rate set" rather than letting
  // the toggle (and Both mode's direct toDonorAmount calls, which skip
  // AmountDisplay's own `!rate` guard) render €Infinity.
  const showCurrencyToggle = rate != null && rate > 0;
  const extraFieldKeys = useMemo((): string[] => {
    const keys = new Set<string>();
    if (!lines) return [];
    lines.forEach((line) => {
      if (line.extra_fields) {
        Object.keys(line.extra_fields).forEach((key) => keys.add(key));
      }
    });
    return Array.from(keys);
  }, [lines]);

  const mutation = useMutation({
    mutationFn: (budget_line_id: string) => {
      // Call the API to delete the budget line
      return deleteBudgetLine(budget_line_id);
    },
    onSuccess: (_, budget_line_id) => {
      // On success, you might want to refetch the budget lines or update the state
      if (!budget) return;
      console.log(
        `Budget line with id ${budget_line_id} deleted successfully.`,
      );
      const updatedBudget = {
        ...budget,
        lines: budget.lines?.filter((line) => line.id !== budget_line_id),
      };
      setBudget(updatedBudget);
    },
    onError: (error) => {
      console.error("Error deleting budget line:", error);
    },
  });

  const onDelete = (budget_line_id: string) => {
    console.log("Delete clicked for line id:", budget_line_id);
    mutation.mutate(budget_line_id);
  };
  const localCode = budget?.local_currency ?? "local";
  const donorCode = budget?.actual_currency ?? "donor";

  const columns = useMemo<ColumnDef<BudgetLine>[]>(() => {
    // Amount: one column per currency when both are requested at once,
    // each header stating its own currency so no cell needs an inline
    // "(est.)" suffix repeated on every row (see budget-view-redesign
    // proposal, note 6). Local/Donor-only modes stay a single column.
    const amountColumns: ColumnDef<BudgetLine>[] =
      displayMode === "both"
        ? [
            {
              header: `Amount (${localCode})`,
              id: "amount_local",
              accessorFn: (row: BudgetLine) => row.amount ?? 0,
              cell: (info) => (
                <span className="font-semibold text-slate-800">
                  {formatCurrency(info.getValue<number>(), localCode)}
                </span>
              ),
              aggregationFn: "sum",
              aggregatedCell: (info) => (
                <span className="font-semibold text-slate-800">
                  Subtotal:{" "}
                  {formatCurrency(info.getValue() as number, localCode)}
                </span>
              ),
            },
            {
              header: `Amount (${donorCode} est.)`,
              id: "amount_donor",
              accessorFn: (row: BudgetLine) => row.amount ?? 0,
              cell: (info) => (
                <span className="font-semibold text-slate-800">
                  {formatCurrency(
                    toDonorAmount(info.getValue<number>(), rate!),
                    donorCode,
                  )}
                </span>
              ),
              aggregationFn: "sum",
              aggregatedCell: (info) => (
                <span className="font-semibold text-slate-800">
                  Subtotal:{" "}
                  {formatCurrency(
                    toDonorAmount(info.getValue() as number, rate!),
                    donorCode,
                  )}
                </span>
              ),
            },
          ]
        : [
            {
              header:
                displayMode === "donor"
                  ? `Amount (${donorCode} est.)`
                  : `Amount (${localCode})`,
              accessorKey: "amount",
              cell: (info) => (
                <span className="font-semibold text-slate-800">
                  <AmountDisplay
                    localAmount={info.getValue<number>()}
                    mode={displayMode}
                    localCurrency={budget?.local_currency}
                    actualCurrency={budget?.actual_currency}
                    rate={rate}
                    labelInline={false}
                  />
                </span>
              ),
              aggregationFn: "sum",
              aggregatedCell: (info) => {
                const value = info.getValue() as number;
                return (
                  <span className="font-semibold text-slate-800">
                    Subtotal:{" "}
                    <AmountDisplay
                      localAmount={value}
                      mode={displayMode}
                      localCurrency={budget?.local_currency}
                      actualCurrency={budget?.actual_currency}
                      rate={rate}
                      labelInline={false}
                    />
                  </span>
                );
              },
            },
          ];

    const cols: ColumnDef<BudgetLine>[] = [
      {
        header: "Category",
        accessorFn: (row) => row.category?.name ?? "—",
        id: "category",
        enableSorting: true,
        enableGrouping: true,
      },
      {
        header: "Description",
        accessorKey: "description",
        enableSorting: true,
      },
      ...amountColumns,
      {
        header: displayMode === "donor" ? `Used (${donorCode} est.)` : "Used",
        id: "used",
        accessorFn: (row: BudgetLine) => spendByLineId[row.id] ?? 0,
        aggregationFn: "sum",
        cell: (info) => (
          <UsedPill
            used={info.getValue<number>()}
            allocated={info.row.original.amount ?? 0}
            currency={budget?.local_currency}
            displayMode={displayMode}
            actualCurrency={budget?.actual_currency}
            rate={rate}
            labelInline={displayMode === "both"}
            loading={isSpendPending}
          />
        ),
        aggregatedCell: (info) => (
          <UsedPill
            used={info.getValue() as number}
            allocated={(info.row.getValue("amount") as number) ?? 0}
            currency={budget?.local_currency}
            displayMode={displayMode}
            actualCurrency={budget?.actual_currency}
            rate={rate}
            labelInline={displayMode === "both"}
            loading={isSpendPending}
          />
        ),
      },
      // Dynamically add columns for extra_fields
      ...extraFieldKeys.map((key: string) => ({
        header: key,
        accessorFn: (row: BudgetLine) => row.extra_fields?.[key] ?? "—",
        id: key, // important for unique identification
      })),
    ];

    if (!readOnly) {
      cols.push(
        columnHelper.display({
          id: "actions",
          enableSorting: false,
          cell: (info) => (
            <div className="flex items-center space-x-1">
              <Button
                variant="icon"
                onClick={() => onEdit(info.row.original)}
                title="Edit line"
              >
                <Edit2 size={16} />
              </Button>

              <ConfirmDeleteButton
                variant="icon-danger"
                title="Delete line"
                onConfirm={() => onDelete(info.row.original.id)}
              >
                <Trash2 size={16} />
              </ConfirmDeleteButton>
            </div>
          ),
        }),
      );
    }

    return cols;
  }, [
    extraFieldKeys,
    readOnly,
    budget?.local_currency,
    budget?.actual_currency,
    spendByLineId,
    isSpendPending,
    displayMode,
    rate,
    localCode,
    donorCode,
  ]);

  // react-table caches each row's computed cell values keyed off `data`'s
  // reference alone, oblivious to accessorFn closing over spendByLineId —
  // force a cache bust when spend data changes (#216).
  const tableData = useMemo(() => [...(lines ?? [])], [lines, spendByLineId]);

  // Mobile card list: same data as the desktop table, grouped by category
  // like TableCommon's grouping does, but always-expanded (no separate
  // collapse state) — simpler, and mobile users are scrolling vertically
  // anyway. Table.tsx/TableCommon has no card-fallback mode, so this is
  // hand-rolled, same pattern as BudgetReportsPage's mobile cards.
  const groupedByCategory = useMemo(() => {
    const groups = new Map<string, BudgetLine[]>();
    (lines ?? []).forEach((line) => {
      const key = line.category?.name ?? "—";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(line);
    });
    return Array.from(groups.entries());
  }, [lines]);

  return (
    <div className="w-full bg-white rounded-xl border border-slate-200 shadow-sm p-6">
      <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <h2 className="text-section-title">Budget Lines</h2>
        <div className="flex items-center gap-3">
          {showCurrencyToggle && (
            <div
              className="flex space-x-2"
              role="group"
              aria-label="Currency display"
            >
              <Button
                variant="toggle"
                active={displayMode === "local"}
                onClick={() => setDisplayMode("local")}
                className="text-xs px-2 py-1"
              >
                Local
              </Button>
              <Button
                variant="toggle"
                active={displayMode === "donor"}
                onClick={() => setDisplayMode("donor")}
                className="text-xs px-2 py-1"
              >
                Donor (estimated)
              </Button>
              <Button
                variant="toggle"
                active={displayMode === "both"}
                onClick={() => setDisplayMode("both")}
                className="text-xs px-2 py-1"
              >
                Both
              </Button>
            </div>
          )}
          {!readOnly && (
            <Button variant="primary" onClick={onNew} className="text-sm">
              New Budget Line
            </Button>
          )}
        </div>
      </div>

      <div className="hidden sm:block">
        <TableCommon data={tableData} columns={columns} bare />
      </div>

      <div className="sm:hidden flex flex-col gap-4">
        {groupedByCategory.length === 0 ? (
          <p className="text-sm text-slate-500">No budget lines yet.</p>
        ) : (
          groupedByCategory.map(([categoryName, categoryLines]) => {
            const subtotal = categoryLines.reduce(
              (sum, l) => sum + (l.amount ?? 0),
              0,
            );
            const categoryUsed = categoryLines.reduce(
              (sum, l) => sum + (spendByLineId[l.id] ?? 0),
              0,
            );
            return (
              <div
                key={categoryName}
                className="border border-slate-200 rounded-lg"
              >
                <div className="flex items-center justify-between gap-3 px-3 py-2 bg-slate-50 rounded-t-lg">
                  <span className="text-sm font-semibold text-slate-700">
                    {categoryName}{" "}
                    <span className="text-slate-400 font-normal">
                      ({categoryLines.length})
                    </span>
                  </span>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold text-slate-800">
                      <AmountDisplay
                        localAmount={subtotal}
                        mode={displayMode}
                        localCurrency={budget?.local_currency}
                        actualCurrency={budget?.actual_currency}
                        rate={rate}
                      />
                    </span>
                    <UsedPill
                      used={categoryUsed}
                      allocated={subtotal}
                      currency={budget?.local_currency}
                      displayMode={displayMode}
                      actualCurrency={budget?.actual_currency}
                      rate={rate}
                      loading={isSpendPending}
                    />
                  </div>
                </div>
                <div className="divide-y divide-slate-100">
                  {categoryLines.map((line) => (
                    <div key={line.id} className="p-3 flex flex-col gap-2">
                      <div className="flex items-start justify-between gap-3">
                        <span className="text-sm text-slate-700">
                          {line.description}
                        </span>
                        <span className="text-sm font-semibold text-slate-800 whitespace-nowrap">
                          <AmountDisplay
                            localAmount={line.amount ?? 0}
                            mode={displayMode}
                            localCurrency={budget?.local_currency}
                            actualCurrency={budget?.actual_currency}
                            rate={rate}
                          />
                        </span>
                      </div>
                      <UsedPill
                        used={spendByLineId[line.id] ?? 0}
                        allocated={line.amount ?? 0}
                        currency={budget?.local_currency}
                        displayMode={displayMode}
                        actualCurrency={budget?.actual_currency}
                        rate={rate}
                        loading={isSpendPending}
                      />
                      {extraFieldKeys
                        .filter((key) => line.extra_fields?.[key] !== undefined)
                        .map((key) => (
                          <div key={key} className="text-xs text-slate-500">
                            <span className="font-medium text-slate-600">
                              {key}:
                            </span>{" "}
                            {String(line.extra_fields?.[key] ?? "—")}
                          </div>
                        ))}
                      {!readOnly && (
                        <div className="flex items-center gap-1 pt-1">
                          <Button
                            variant="icon"
                            onClick={() => onEdit(line)}
                            title="Edit line"
                          >
                            <Edit2 size={16} />
                          </Button>
                          <ConfirmDeleteButton
                            variant="icon-danger"
                            title="Delete line"
                            onConfirm={() => onDelete(line.id)}
                          >
                            <Trash2 size={16} />
                          </ConfirmDeleteButton>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
