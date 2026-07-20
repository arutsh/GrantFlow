import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { BudgetViewHeader } from "./components/BudgetViewHeader";
import { BudgetViewLinesTable } from "./components/BudgetViewLinesTable";
import { BudgetViewTraces } from "./components/BudgetViewTraces";
import { BudgetViewSummary } from "./components/BudgetViewSummary";
import { AddBudgetLineModal } from "./components/AddBudgetLine";
import { Budget, BudgetLine } from "./types/budget";
import {
  SingleBudgetViewContextProvider,
  useDetailedBudget,
} from "./SingleBudgetViewContext";
import { editBudget } from "@/api/budgetApi";
import { budgetDetailsQueryKey } from "./queryKeys";
import {
  createBudgetLine,
  deleteBudgetLine,
  updateBudgetLines,
} from "@/api/gatewayApi";
import Button from "@/components/ui/Button";

// ─── Types ────────────────────────────────────────────────────────────────────

interface DraftLine {
  _key: string;
  id?: string;
  category_name: string;
  description: string;
  amount: number;
}

// ─── Container ────────────────────────────────────────────────────────────────

export function SingleBudgetViewContainer() {
  const { id } = useParams<{ id: string }>();
  return (
    <SingleBudgetViewContextProvider id={id}>
      <SingleBudgetView id={id} />
    </SingleBudgetViewContextProvider>
  );
}

// ─── View ─────────────────────────────────────────────────────────────────────

function SingleBudgetView({ id }: { id: string | undefined }) {
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isEditLineOpen, setIsEditLineOpen] = useState<BudgetLine | undefined>(
    undefined
  );
  const [isEditMode, setIsEditMode] = useState(false);
  const { budget, setBudget } = useDetailedBudget();
  const queryClient = useQueryClient();

  useEffect(() => {
    if (budget?.status === "ai_draft") {
      setIsEditMode(true);
    }
  }, [budget?.status]);

  return (
    <>
      {isAddOpen && (
        <AddBudgetLineModal
          isOpen={isAddOpen}
          onClose={() => setIsAddOpen(false)}
          budgetLine={undefined}
          onSave={() => {}}
        />
      )}
      {isEditLineOpen && (
        <AddBudgetLineModal
          budgetLine={isEditLineOpen}
          isOpen={!!isEditLineOpen}
          onClose={() => setIsEditLineOpen(undefined)}
          onSave={() => {}}
        />
      )}
      {budget && (
        <div className="flex flex-col items-center px-10 min-h-screen bg-gray-50">
          {isEditMode ? (
            <BudgetEditMode
              budget={budget}
              onSaved={(updated) => {
                setBudget(updated);
                queryClient.invalidateQueries({
                  queryKey: budgetDetailsQueryKey(id),
                });
                setIsEditMode(false);
              }}
              onDiscard={() => setIsEditMode(false)}
            />
          ) : (
            <>
              <div className="w-full flex justify-end pt-4">
                <Button
                  variant="secondary"
                  onClick={() => setIsEditMode(true)}
                  className="text-sm"
                >
                  Edit
                </Button>
              </div>
              <BudgetViewHeader budget={budget} />
              <BudgetViewSummary />
              <BudgetViewLinesTable
                lines={budget.lines}
                onEdit={(value) => setIsEditLineOpen(value)}
                onNew={() => setIsAddOpen(true)}
                onClose={() => {
                  setIsAddOpen(false);
                  setIsEditLineOpen(undefined);
                }}
              />
              <BudgetViewTraces budget={budget} />
            </>
          )}
        </div>
      )}
    </>
  );
}

// ─── Inline Edit Mode ─────────────────────────────────────────────────────────

function BudgetEditMode({
  budget,
  onSaved,
  onDiscard,
}: {
  budget: Budget;
  onSaved: (updated: Budget) => void;
  onDiscard: () => void;
}) {
  const [name, setName] = useState(budget.name ?? "");
  const [funderName, setFunderName] = useState(
    (budget.funder as { name?: string } | null)?.name ?? ""
  );
  const [durationMonths, setDurationMonths] = useState<number | "">(
    budget.duration_months ?? ""
  );
  const [draftLines, setDraftLines] = useState<DraftLine[]>(() =>
    (budget.lines ?? []).map((l) => ({
      _key: l.id,
      id: l.id,
      category_name: l.category?.name ?? "",
      description: l.description,
      amount: l.amount,
    }))
  );
  const [deletedIds, setDeletedIds] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const totalAmount = draftLines.reduce((s, l) => s + Number(l.amount), 0);

  const handleLineChange = (
    key: string,
    field: keyof Omit<DraftLine, "_key" | "id">,
    value: string | number
  ) => {
    setDraftLines((prev) =>
      prev.map((l) => (l._key === key ? { ...l, [field]: value } : l))
    );
  };

  const handleAddLine = () => {
    setDraftLines((prev) => [
      ...prev,
      {
        _key: crypto.randomUUID(),
        category_name: "",
        description: "",
        amount: 0,
      },
    ]);
  };

  const handleDeleteLine = (key: string) => {
    const line = draftLines.find((l) => l._key === key);
    if (line?.id) setDeletedIds((prev) => [...prev, line.id!]);
    setDraftLines((prev) => prev.filter((l) => l._key !== key));
  };

  const handleSave = async () => {
    if (!budget.id) return;
    setIsSaving(true);
    setError("");
    try {
      const updatedMeta = await editBudget(budget.id, {
        name: name.trim() || undefined,
        external_funder_name: funderName.trim() || undefined,
        duration_months: durationMonths !== "" ? Number(durationMonths) : undefined,
        status: "draft",
      });

      await Promise.all([
        ...draftLines.map((l) =>
          l.id
            ? updateBudgetLines({
                id: l.id,
                budget_id: budget.id,
                description: l.description,
                amount: l.amount,
                category_name: l.category_name,
              } as BudgetLine)
            : createBudgetLine({
                budget_id: budget.id,
                description: l.description,
                amount: l.amount,
                category_name: l.category_name,
              })
        ),
        ...deletedIds.map((lid) => deleteBudgetLine(lid)),
      ]);

      onSaved({ ...budget, ...updatedMeta, status: "draft" });
    } catch {
      setError("Failed to save changes. Please try again.");
      setIsSaving(false);
    }
  };

  return (
    <div className="w-full pt-6 space-y-6">
      {/* Edit header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h2 className="text-xl font-semibold text-slate-800">Edit Budget</h2>
          {budget.status === "ai_draft" && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full font-medium">
              AI Draft
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={onDiscard} disabled={isSaving}>
            Discard
          </Button>
          <Button
            variant="primary"
            onClick={handleSave}
            disabled={isSaving || !name.trim()}
          >
            {isSaving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {/* Metadata fields */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-white border border-slate-200 rounded-xl p-5">
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Budget Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Funder Name
          </label>
          <input
            type="text"
            value={funderName}
            onChange={(e) => setFunderName(e.target.value)}
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-500 mb-1">
            Duration (months)
          </label>
          <input
            type="number"
            min={1}
            value={durationMonths}
            onChange={(e) =>
              setDurationMonths(
                e.target.value ? parseInt(e.target.value) : ""
              )
            }
            className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
          />
        </div>
      </div>

      {/* Lines table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200">
          <span className="text-sm font-semibold text-slate-700">
            Budget Lines
          </span>
          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-500">
              Total: ${totalAmount.toLocaleString()}
            </span>
            <Button
              variant="secondary"
              onClick={handleAddLine}
              className="text-xs py-1 px-3"
            >
              + Add Line
            </Button>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-3 py-2 font-medium text-slate-600">
                  Category
                </th>
                <th className="text-left px-3 py-2 font-medium text-slate-600">
                  Description
                </th>
                <th className="text-right px-3 py-2 font-medium text-slate-600">
                  Amount ($)
                </th>
                <th className="px-2 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {draftLines.map((line) => (
                <tr key={line._key} className="hover:bg-slate-50">
                  <td className="px-3 py-1.5">
                    <input
                      type="text"
                      value={line.category_name}
                      onChange={(e) =>
                        handleLineChange(line._key, "category_name", e.target.value)
                      }
                      className="w-full bg-transparent border border-transparent focus:border-slate-300 rounded px-1 py-0.5 focus:outline-none"
                      placeholder="Category"
                    />
                  </td>
                  <td className="px-3 py-1.5">
                    <input
                      type="text"
                      value={line.description}
                      onChange={(e) =>
                        handleLineChange(line._key, "description", e.target.value)
                      }
                      className="w-full bg-transparent border border-transparent focus:border-slate-300 rounded px-1 py-0.5 focus:outline-none"
                      placeholder="Description"
                    />
                  </td>
                  <td className="px-3 py-1.5">
                    <input
                      type="number"
                      min={0}
                      value={line.amount}
                      onChange={(e) =>
                        handleLineChange(
                          line._key,
                          "amount",
                          parseFloat(e.target.value) || 0
                        )
                      }
                      className="w-full text-right bg-transparent border border-transparent focus:border-slate-300 rounded px-1 py-0.5 focus:outline-none"
                    />
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    <button
                      onClick={() => handleDeleteLine(line._key)}
                      title="Remove line"
                      className="text-slate-400 hover:text-red-500 transition-colors text-xs px-1"
                    >
                      ✕
                    </button>
                  </td>
                </tr>
              ))}
              {draftLines.length === 0 && (
                <tr>
                  <td
                    colSpan={4}
                    className="px-5 py-6 text-center text-sm text-slate-400"
                  >
                    No lines yet — click "+ Add Line" to start.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default SingleBudgetView;
