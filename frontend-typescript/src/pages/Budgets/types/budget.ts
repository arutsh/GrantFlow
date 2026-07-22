export interface UserOut {
  id?: string;
  first_name?: string;
  last_name?: string;
  email?: string;
}

export interface CustomerOut {
  id?: string;
  name?: string;
  is_ngo?: boolean;
  is_donor?: boolean;
}

export interface TraceEvent {
  user?: UserOut;
  event_date?: string | null; // ISO date string
}

export interface TraceOut {
  created?: TraceEvent;
  updated?: TraceEvent;
}
export interface BudgetCategory {
  id: string;
  name: string;
  code: string;
  donor_template_id?: string;
}

export interface NewBudgetLine {
  budget_id: string;
  description: string;
  amount: number;
  extra_fields?: Record<string, string>;
  category_name?: string;
  category_id?: string;
}

export interface BudgetLine extends NewBudgetLine {
  id: string;
  category?: BudgetCategory;
}

export interface Budget {
  id: string;
  name?: string;
  status: string;
  duration_months?: number;
  local_currency?: string;
  total_amount?: number;
  owner?: CustomerOut;
  funder?: CustomerOut | { name?: string; id?: string };
  trace?: TraceOut;
  lines?: BudgetLine[];
}

// Define a separate type for editing (input data)
export interface BudgetUpdate {
  name?: string;
  owner_id?: string;
  funding_customer_id?: string;
  external_funder_name?: string;
  duration_months?: number;
  status?: string;
}

export interface BudgetPatched {
  id: string;
  name?: string;
  owner_id?: string;
  funding_customer_id?: string;
  external_funder_name?: string;
  status?: string;
  duration_months?: number;
  local_currency?: string;
}

export interface BudgetLinePreview {
  category_name: string;
  description: string;
  amount: number;
  extra_fields?: Record<string, unknown> | null;
}

export interface ParseBudgetResponse {
  budget_name: string;
  external_funder_name: string | null;
  duration_months: number | null;
  lines: BudgetLinePreview[];
  ai_available: boolean;
  prompt_version: string;
}

export interface CreateBudgetWithLinesRequest {
  budget_name: string;
  external_funder_name: string;
  duration_months?: number | null;
  lines: BudgetLinePreview[];
}
