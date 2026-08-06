import React, { useEffect, useState, useMemo } from "react";
import Input from "@/components/ui/Input";
import Button from "@/components/ui/Button";
import {
  useMutation,
  useQueries,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { fetchAllBudgets } from "@/api/gatewayApi";
import { utcToLocal } from "@/utils/datetime";
import { HiPlus } from "react-icons/hi";
import { HiXMark, HiMagnifyingGlass } from "react-icons/hi2";
import { TableView } from "./components/TableView";
import { CardsView } from "./components/CardsView";

import { CardTableToggle } from "@/components/ui/CardTableToggle";
import { Budget, BudgetPatched } from "./types/budget";
import { archiveBudget, deleteBudget } from "@/api/budgetApi";
import { AddBudgetModal } from "./components/AddBudget";
import { EditBudgetModal } from "./components/EditBudget";

const BudgetsPage: React.FC = () => {
  const [view, setView] = useState<"cards" | "table">();
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [editingBudget, setEditingBudget] = useState<Budget | null>(null);
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768);

  // Filter states
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatuses, setFilterStatuses] = useState<string[]>([]);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);
  const [filterCurrencies, setFilterCurrencies] = useState<string[]>([]);
  const [showCurrencyDropdown, setShowCurrencyDropdown] = useState(false);
  const [filterDuration, setFilterDuration] = useState<string>("");
  const [showDurationDropdown, setShowDurationDropdown] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      // Auto-switch: cards on mobile, table on desktop
      if (mobile && view === "table") {
        setView("cards");
      } else if (!mobile && view === undefined) {
        setView("table");
      }
    };

    window.addEventListener("resize", handleResize);
    // Set initial view
    if (view === undefined) {
      setView(isMobile ? "cards" : "table");
    }
    return () => window.removeEventListener("resize", handleResize);
  }, [isMobile, view]);

  const queryClient = useQueryClient();
  const openEditModal = (budget: Budget) => {
    setEditingBudget(budget);

    setIsEditOpen(true);
  };

  const closeAddModal = (newBudget: Budget | null) => {
    if (newBudget) {
      queryClient.setQueryData(["budgets"], (oldData: Budget[] | undefined) => {
        if (!oldData) return [];
        return [...oldData, newBudget];
      });
    }
    setIsAddOpen(false);
  };

  const closeEditModal = (updatedBudget: BudgetPatched | null) => {
    if (updatedBudget) {
      queryClient.setQueryData(["budgets"], (oldData: Budget[] | undefined) => {
        if (!oldData) return [];
        return oldData.map((b) => {
          if (b.id === updatedBudget.id) {
            b.name = updatedBudget.name;
            b.funder = {};
            b.funder.name = updatedBudget?.external_funder_name;
            b.funder.id = updatedBudget?.funding_customer_id ?? undefined;
          }
          return b;
        });
      });
    }
    setEditingBudget(null);
    setIsEditOpen(false);
  };
  const deleteBudgetMutation = useMutation({
    mutationFn: async (budgetId: string) => archiveBudget(budgetId),
    onSuccess: (_, budgetId) => {
      // Invalidate and refetch budgets after deletion
      queryClient.setQueryData(["budgets"], (oldData: Budget[] | undefined) => {
        if (!oldData) return [];
        return oldData.filter((b) => b.id !== budgetId);
      });
    },
  });
  const { isPending, isError, data, error } = useQuery({
    queryKey: ["budgets"],
    queryFn: fetchAllBudgets,
  });

  // Filter logic
  const filteredData = useMemo(() => {
    if (!data) return [];

    return data.filter((budget: Budget) => {
      const matchesSearch =
        (budget.name?.toLowerCase() ?? "").includes(searchTerm.toLowerCase()) ||
        (budget.funder?.name?.toLowerCase() ?? "").includes(
          searchTerm.toLowerCase(),
        );

      const matchesStatus =
        filterStatuses.length === 0 || filterStatuses.includes(budget.status);
      const matchesCurrency =
        filterCurrencies.length === 0 ||
        (budget.local_currency &&
          filterCurrencies.includes(budget.local_currency));

      let matchesDuration = true;
      if (filterDuration) {
        const duration = budget.duration_months || 0;
        if (filterDuration === "short") matchesDuration = duration <= 6;
        if (filterDuration === "medium")
          matchesDuration = duration > 6 && duration <= 12;
        if (filterDuration === "long") matchesDuration = duration > 12;
      }

      return (
        matchesSearch && matchesStatus && matchesCurrency && matchesDuration
      );
    });
  }, [data, searchTerm, filterStatuses, filterCurrencies, filterDuration]);

  // Get unique values for filters
  const uniqueStatuses = useMemo(() => {
    if (!data) return [];
    const statuses = new Set<string>();
    data.forEach((b: Budget) => {
      if (b.status) statuses.add(b.status);
    });
    return Array.from(statuses);
  }, [data]);

  const uniqueCurrencies = useMemo(() => {
    if (!data) return [];
    const currencies = new Set<string>();
    data.forEach((b: Budget) => {
      if (b.local_currency) currencies.add(b.local_currency);
    });
    return Array.from(currencies);
  }, [data]);

  const clearFilters = () => {
    setSearchTerm("");
    setFilterStatuses([]);
    setFilterCurrencies([]);
    setFilterDuration("");
  };

  if (isPending) {
    return <div>Loading...</div>;
  }

  if (isError) {
    return <div>Error: {error.message}</div>;
  }

  return (
    <>
      {isEditOpen && editingBudget && (
        <EditBudgetModal
          isOpen={isEditOpen}
          onClose={(val) => closeEditModal(val)}
          data={editingBudget}
        />
      )}
      {isAddOpen && (
        <AddBudgetModal
          isOpen={isAddOpen}
          onClose={(val) => closeAddModal(val)}
        />
      )}
      <div className="-m-8 flex h-screen overflow-hidden">
        {/* Main scrollable area */}
        <div className="flex-1 min-w-0 overflow-auto p-8 bg-gray-50 flex flex-col">
          {/* Header Section */}
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-slate-900 mb-2">Budgets</h1>
            <p className="text-gray-600">
              Manage and track all your budgets in one place.
            </p>
          </div>

          {/* Controls Section */}
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 mb-8">
            <div className="flex gap-3 w-full md:w-auto">
              <Button
                onClick={() => setIsAddOpen(!isAddOpen)}
                variant="primary"
                className="flex items-center gap-2"
              >
                <HiPlus size={18} /> Add Budget
              </Button>
            </div>
            {!isMobile && view && (
              <CardTableToggle
                view={view}
                onViewChange={(newView) => setView(newView)}
              />
            )}
          </div>

          {/* Filter Section */}
          <div className="mb-6 p-4 bg-white rounded-lg border border-slate-200 shadow-sm">
            {/* Selected Filters Display */}
            {(filterStatuses.length > 0 ||
              filterCurrencies.length > 0 ||
              filterDuration) && (
              <div className="mb-4 flex flex-wrap gap-2">
                {filterStatuses.map((status: string) => (
                  <div
                    key={`status-${status}`}
                    className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold capitalize ${
                      status === "draft"
                        ? "bg-yellow-100 text-yellow-800"
                        : status === "approved"
                          ? "bg-green-100 text-green-800"
                          : status === "rejected"
                            ? "bg-red-100 text-red-800"
                            : "bg-slate-100 text-slate-800"
                    }`}
                  >
                    {status}
                    <button
                      onClick={() =>
                        setFilterStatuses(
                          filterStatuses.filter((s) => s !== status),
                        )
                      }
                      className="hover:opacity-70 transition-opacity"
                    >
                      <HiXMark size={16} />
                    </button>
                  </div>
                ))}
                {filterCurrencies.map((currency: string) => (
                  <div
                    key={`currency-${currency}`}
                    className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold bg-blue-100 text-blue-800"
                  >
                    {currency}
                    <button
                      onClick={() =>
                        setFilterCurrencies(
                          filterCurrencies.filter((c) => c !== currency),
                        )
                      }
                      className="hover:opacity-70 transition-opacity"
                    >
                      <HiXMark size={16} />
                    </button>
                  </div>
                ))}
                {filterDuration && (
                  <div className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold bg-purple-100 text-purple-800">
                    {filterDuration === "short"
                      ? "≤ 6 mo"
                      : filterDuration === "medium"
                        ? "7-12 mo"
                        : "> 12 mo"}
                    <button
                      onClick={() => setFilterDuration("")}
                      className="hover:opacity-70 transition-opacity"
                    >
                      <HiXMark size={16} />
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Filter Controls - Single Row */}
            <div className="flex flex-col lg:flex-row items-start lg:items-center gap-3">
              {/* Search Bar - Smaller */}
              <div className="relative flex-shrink-0 w-full lg:w-64">
                <HiMagnifyingGlass className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-9 pr-3 py-2 w-full border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-slate-400"
                />
              </div>

              {/* Status Filter - Multi-select with Dropdown */}
              <div className="relative flex-shrink-0 w-full lg:w-auto">
                <button
                  onClick={() => setShowStatusDropdown(!showStatusDropdown)}
                  className="w-full lg:w-auto px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white hover:bg-slate-50 flex items-center justify-between gap-2 focus:outline-none focus:ring-2 focus:ring-slate-400"
                >
                  <span className="text-slate-700">
                    {filterStatuses.length === 0
                      ? "Status"
                      : `${filterStatuses.length} selected`}
                  </span>
                  <svg
                    className={`w-4 h-4 text-slate-400 transition-transform ${showStatusDropdown ? "rotate-180" : ""}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 14l-7 7m0 0l-7-7m7 7V3"
                    />
                  </svg>
                </button>

                {/* Status Dropdown */}
                {showStatusDropdown && (
                  <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-slate-300 rounded-lg shadow-lg z-10">
                    <div className="p-2">
                      {uniqueStatuses.map((status: string) => (
                        <label
                          key={status}
                          className="flex items-center gap-2 px-3 py-2 rounded hover:bg-slate-50 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={filterStatuses.includes(status)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setFilterStatuses([...filterStatuses, status]);
                              } else {
                                setFilterStatuses(
                                  filterStatuses.filter((s) => s !== status),
                                );
                              }
                            }}
                            className="w-4 h-4 rounded border-slate-300 text-slate-700 focus:ring-slate-400"
                          />
                          <span className="text-sm text-slate-700 capitalize">
                            {status}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Currency Filter - Multi-select with Dropdown */}
              <div className="relative flex-shrink-0 w-full lg:w-auto">
                <button
                  onClick={() => setShowCurrencyDropdown(!showCurrencyDropdown)}
                  className="w-full lg:w-auto px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white hover:bg-slate-50 flex items-center justify-between gap-2 focus:outline-none focus:ring-2 focus:ring-slate-400"
                >
                  <span className="text-slate-700">
                    {filterCurrencies.length === 0
                      ? "Currency"
                      : `${filterCurrencies.length} selected`}
                  </span>
                  <svg
                    className={`w-4 h-4 text-slate-400 transition-transform ${showCurrencyDropdown ? "rotate-180" : ""}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 14l-7 7m0 0l-7-7m7 7V3"
                    />
                  </svg>
                </button>

                {/* Currency Dropdown */}
                {showCurrencyDropdown && (
                  <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-slate-300 rounded-lg shadow-lg z-10">
                    <div className="p-2">
                      {uniqueCurrencies.map((currency: string) => (
                        <label
                          key={currency}
                          className="flex items-center gap-2 px-3 py-2 rounded hover:bg-slate-50 cursor-pointer"
                        >
                          <input
                            type="checkbox"
                            checked={filterCurrencies.includes(currency)}
                            onChange={(e) => {
                              if (e.target.checked) {
                                setFilterCurrencies([
                                  ...filterCurrencies,
                                  currency,
                                ]);
                              } else {
                                setFilterCurrencies(
                                  filterCurrencies.filter(
                                    (c) => c !== currency,
                                  ),
                                );
                              }
                            }}
                            className="w-4 h-4 rounded border-slate-300 text-slate-700 focus:ring-slate-400"
                          />
                          <span className="text-sm text-slate-700">
                            {currency}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Duration Filter - Single select with Dropdown */}
              <div className="relative flex-shrink-0 w-full lg:w-auto">
                <button
                  onClick={() => setShowDurationDropdown(!showDurationDropdown)}
                  className="w-full lg:w-auto px-3 py-2 border border-slate-300 rounded-lg text-sm bg-white hover:bg-slate-50 flex items-center justify-between gap-2 focus:outline-none focus:ring-2 focus:ring-slate-400"
                >
                  <span className="text-slate-700">
                    {filterDuration === ""
                      ? "Duration"
                      : filterDuration === "short"
                        ? "≤ 6 mo"
                        : filterDuration === "medium"
                          ? "7-12 mo"
                          : "> 12 mo"}
                  </span>
                  <svg
                    className={`w-4 h-4 text-slate-400 transition-transform ${showDurationDropdown ? "rotate-180" : ""}`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M19 14l-7 7m0 0l-7-7m7 7V3"
                    />
                  </svg>
                </button>

                {/* Duration Dropdown */}
                {showDurationDropdown && (
                  <div className="absolute top-full left-0 mt-1 w-56 bg-white border border-slate-300 rounded-lg shadow-lg z-10">
                    <div className="p-2">
                      {[
                        { value: "short", label: "Short (≤ 6 mo)" },
                        { value: "medium", label: "Medium (7-12 mo)" },
                        { value: "long", label: "Long (> 12 mo)" },
                      ].map((option) => (
                        <label
                          key={option.value}
                          className="flex items-center gap-2 px-3 py-2 rounded hover:bg-slate-50 cursor-pointer"
                        >
                          <input
                            type="radio"
                            name="duration"
                            value={option.value}
                            checked={filterDuration === option.value}
                            onChange={(e) => {
                              setFilterDuration(e.target.value);
                              setShowDurationDropdown(false);
                            }}
                            className="w-4 h-4 border-slate-300 text-slate-700 focus:ring-slate-400"
                          />
                          <span className="text-sm text-slate-700">
                            {option.label}
                          </span>
                        </label>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Clear Button */}
              {(searchTerm ||
                filterStatuses.length > 0 ||
                filterCurrencies.length > 0 ||
                filterDuration) && (
                <Button
                  onClick={clearFilters}
                  variant="outline"
                  className="w-full lg:w-auto flex items-center justify-center gap-1 py-2 px-3"
                >
                  <HiXMark size={14} /> Clear All
                </Button>
              )}
            </div>

            {/* Results counter */}
            <div className="text-xs text-slate-600 mt-3">
              {filteredData.length} of {data?.length || 0} budgets
            </div>
          </div>

          {/* Content Section */}
          {filteredData && filteredData.length > 0 ? (
            <>
              {view === "cards" ? (
                <CardsView
                  data={filteredData}
                  onEdit={openEditModal}
                  onDelete={deleteBudgetMutation.mutate}
                />
              ) : view === "table" ? (
                <TableView
                  data={filteredData}
                  onEdit={openEditModal}
                  onDelete={deleteBudgetMutation.mutate}
                />
              ) : null}
            </>
          ) : (
            <div className="flex items-center justify-center py-16 bg-white rounded-lg border border-slate-200">
              <div className="text-center">
                <div className="mb-4">
                  <HiPlus size={48} className="text-gray-300 mx-auto" />
                </div>
                {data && data.length === 0 ? (
                  <>
                    <p className="text-xl font-semibold text-slate-900 mb-2">
                      No budgets yet
                    </p>
                    <p className="text-gray-600 mb-6">
                      Create your first budget to start managing your finances
                    </p>
                    <Button
                      onClick={() => setIsAddOpen(true)}
                      variant="primary"
                    >
                      Create Your First Budget
                    </Button>
                  </>
                ) : (
                  <>
                    <p className="text-xl font-semibold text-slate-900 mb-2">
                      No budgets match your filters
                    </p>
                    <p className="text-gray-600 mb-6">
                      Try adjusting your search or filter criteria
                    </p>
                    <Button onClick={clearFilters} variant="secondary">
                      Clear Filters
                    </Button>
                  </>
                )}
              </div>
            </div>
          )}
        </div>
        {/* end main scrollable area */}

      </div>
      {/* end outer flex */}
    </>
  );
};

export default BudgetsPage;
