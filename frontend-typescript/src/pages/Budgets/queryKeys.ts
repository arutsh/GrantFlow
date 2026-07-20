// Single source of truth for the budget-detail react-query key — used by the
// fetch (SingleBudgetViewContext), the inline-edit invalidation (SingleBudgetView),
// and the chat-driven-mutation invalidation (AIChatPanel). Keeping this in one
// place means the three call sites can't silently drift out of sync.
export const budgetDetailsQueryKey = (id: string | undefined) => ["budgetDetails", id] as const;
