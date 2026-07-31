import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";

import { useNavigate, useParams } from "react-router-dom";
import DashboardLayout from "../Dashboard/DashboardLayout";
import { fetchBudgetById } from "@/api/gatewayApi";
import { listReportLinesByReport, listReportsByBudget } from "@/api/reportApi";
import { budgetDetailsQueryKey, reportLinesQueryKey, reportsByBudgetQueryKey } from "./queryKeys";

import { BudgetViewHeader } from "./components/BudgetViewHeader";

import { BudgetViewLinesTable } from "./components/BudgetViewLinesTable";
import { BudgetViewTraces } from "./components/BudgetViewTraces";
import { BudgetViewSummary } from "./components/BudgetViewSummary";
import { AddBudgetModal } from "./components/AddBudget";
import { Budget, BudgetCategory, BudgetLine } from "./types/budget";
import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";

interface SingleBudgetViewContextType {
  budget: Budget | null;
  setBudget: (b: Budget | null) => void;
  budgetCategories: BudgetCategory[];
  budgetCategoryNames: string[];
  totalAmount: Number;
  existingExtraKeys?: string[];
  // Reported spend per budget_line_id, summed across every report on this
  // budget (not just one) — see GitHub #174: no backend aggregate endpoint
  // exists yet, so this is an N+1 fetch-and-sum client-side, fine for the
  // usual handful of reports per budget.
  spendByLineId: Record<string, number>;
  totalReported: number;
  // isAddOpen: boolean;
  // openAddModal: () => void;
  // closeAddModal: () => void;
}
const SingleBudgetViewContext = createContext<
  SingleBudgetViewContextType | undefined
>(undefined);

export const SingleBudgetViewContextProvider: React.FC<{
  id: string | undefined;
  children: React.ReactNode;
}> = ({ id, children }) => {
  // const [budget, setBudget] = useState<Budget | null>(null);
  const queryClient = useQueryClient();
  // ✅ Fetch budget here
  const {
    data: budget,
    isPending,
    isError,
    error,
    refetch,
  } = useQuery({
    queryKey: budgetDetailsQueryKey(id),
    queryFn: () => (id ? fetchBudgetById(id) : Promise.resolve(null)),
    enabled: !!id,
  });

  const totalAmount = useMemo(() => {
    if (!budget?.lines) return 0;
    return budget.lines.reduce(
      (sum: number, line: BudgetLine) => sum + (line.amount || 0),
      0,
    );
  }, [budget]);

  // ✅ Derive unique categories from budget lines
  const budgetCategories = useMemo((): BudgetCategory[] => {
    if (!budget?.lines) return [];

    const unique = Object.values(
      budget.lines.reduce(
        (acc: Record<string, BudgetCategory>, { category }: BudgetLine) => {
          if (category && !acc[category.id]) acc[category.id] = category;
          return acc;
        },
        {} as Record<string, BudgetCategory>,
      ),
    );

    return unique as BudgetCategory[];
  }, [budget]);

  const existingExtraKeys = useMemo(() => {
    if (!budget?.lines?.length) return [];
    const keys = new Set<string>();
    for (const line of budget.lines) {
      if (line.extra_fields) {
        Object.keys(line.extra_fields).forEach((key) => keys.add(key));
      }
    }
    return Array.from(keys);
  }, [budget]);

  // ✅ Extract category names from categories
  const budgetCategoryNames = useMemo(() => {
    return budgetCategories
      .filter((c): c is BudgetCategory => c !== null && c !== undefined)
      .map((c) => c.name)
      .filter(Boolean) as string[];
  }, [budgetCategories]);

  // ✅ Wrapper setter (updates both state + query cache)
  const setBudget = (updated: Budget | null) => {
    queryClient.setQueryData(budgetDetailsQueryKey(id), updated);
  };

  const { data: reports } = useQuery({
    queryKey: reportsByBudgetQueryKey(id),
    queryFn: () => (id ? listReportsByBudget(id) : Promise.resolve([])),
    enabled: !!id,
  });

  // combine's result is only recomputed when useQueries' structurally-shared
  // output actually changes, unlike a useMemo keyed on the queries array
  // (which is a new reference every render regardless of data changes).
  const spendByLineId = useQueries({
    queries: (reports ?? []).map((report) => ({
      queryKey: reportLinesQueryKey(report.id),
      queryFn: () => listReportLinesByReport(report.id),
    })),
    combine: (queries) => {
      const totals: Record<string, number> = {};
      queries.forEach((query) => {
        (query.data ?? []).forEach((line) => {
          if (!line.budget_line_id) return;
          totals[line.budget_line_id] = (totals[line.budget_line_id] ?? 0) + (line.amount ?? 0);
        });
      });
      return totals;
    },
  });

  const totalReported = useMemo(
    () => Object.values(spendByLineId).reduce((sum, value) => sum + value, 0),
    [spendByLineId],
  );

  return (
    <SingleBudgetViewContext.Provider
      value={{
        budget,
        setBudget,
        budgetCategories,
        budgetCategoryNames,
        totalAmount,
        existingExtraKeys,
        spendByLineId,
        totalReported,
      }}
    >
      {children}
    </SingleBudgetViewContext.Provider>
  );
};

export const useDetailedBudget = (): SingleBudgetViewContextType => {
  const ctx = useContext(SingleBudgetViewContext);
  if (!ctx)
    throw new Error(
      "useDetailedBudget must be used within a SingleBudgetViewContextProvider",
    );
  return ctx;
};
