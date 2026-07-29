import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { BudgetViewHeader } from "./components/BudgetViewHeader";
import { BudgetViewLinesTable } from "./components/BudgetViewLinesTable";
import { BudgetViewTraces } from "./components/BudgetViewTraces";
import { BudgetViewSummary } from "./components/BudgetViewSummary";
import { AddBudgetLineModal } from "./components/AddBudgetLine";
import { ReportsList } from "./components/ReportsList";
import { Budget, BudgetLine } from "./types/budget";
import {
  SingleBudgetViewContextProvider,
  useDetailedBudget,
} from "./SingleBudgetViewContext";
import { budgetDetailsQueryKey } from "./queryKeys";

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
  const { budget, setBudget } = useDetailedBudget();
  const queryClient = useQueryClient();

  // Metadata/lines lock as soon as the budget is confirmed — a report can
  // only ever be created against an already-confirmed budget, so this is a
  // strictly broader (and correct) gate than "has a report" would be.
  const isLocked = budget?.status === "confirmed";

  const handleBudgetUpdated = (updated: Budget) => {
    // The PATCH response is backed by a bare-scalar schema with no
    // lines/owner/funder/trace — merge onto the existing full budget rather
    // than replacing it, so those fields don't flash empty until the
    // invalidateQueries refetch below resolves.
    setBudget(budget ? { ...budget, ...updated } : updated);
    queryClient.invalidateQueries({ queryKey: budgetDetailsQueryKey(id) });
  };

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
        <div className="w-full min-h-screen bg-gray-50 px-4 py-8">
          <div className="w-full max-w-4xl mx-auto flex flex-col gap-5">
            <BudgetViewHeader
              budget={budget}
              isLocked={isLocked}
              onBudgetUpdated={handleBudgetUpdated}
            />
            <BudgetViewSummary />
            <BudgetViewLinesTable
              lines={budget.lines}
              readOnly={isLocked}
              onEdit={(value) => setIsEditLineOpen(value)}
              onNew={() => setIsAddOpen(true)}
              onClose={() => {
                setIsAddOpen(false);
                setIsEditLineOpen(undefined);
              }}
            />
            <ReportsList budget={budget} />
            <BudgetViewTraces budget={budget} />
          </div>
        </div>
      )}
    </>
  );
}

export default SingleBudgetView;
