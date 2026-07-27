import { safeDecodeToken } from "@/utils/token";
import { getAuthToken } from "@/api/axiosConfig";
import { Budget } from "@/pages/Budgets/types/budget";

interface CustomerClaims {
  customer_id?: string;
}

// UI-only convenience: hides actions the backend would 403 on anyway. The
// backend independently re-checks ownership/review access on every call
// (see services/budget/app/services/report_services.py's is_owner/_can_review)
// — a stale or missing claim here can only hide a button, never expose one.
export function getCurrentCustomerId(): string | null {
  const claims = safeDecodeToken<CustomerClaims>(getAuthToken());
  return claims?.customer_id ?? null;
}

export function isBudgetOwner(
  budget: Budget,
  currentCustomerId: string | null
): boolean {
  if (!currentCustomerId || !budget.owner?.id) return false;
  return budget.owner.id === currentCustomerId;
}

// Mirrors _can_review: a funder (funding_customer_id) reviews if one is set
// in-system, otherwise the budget owner reviews as a fallback.
export function canReviewReport(
  budget: Budget,
  currentCustomerId: string | null
): boolean {
  if (!currentCustomerId) return false;
  if (budget.funder?.id) return budget.funder.id === currentCustomerId;
  return isBudgetOwner(budget, currentCustomerId);
}
