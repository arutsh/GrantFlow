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
  actual_currency?: string;
  start_date?: string | null; // ISO date string
  end_date?: string | null; // ISO date string — computed backend-side from start_date + duration_months
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
  actual_currency?: string;
  start_date?: string;
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
  actual_currency?: string;
  start_date?: string | null;
}

// Reports

export type ReportStatus = "draft" | "submitted" | "approved" | "rejected";

export interface Report {
  id: string;
  budget_id?: string;
  name?: string;
  status: ReportStatus;
  period_start?: string | null; // ISO date string
  period_end?: string | null;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  reviewed_by?: string | null;
  review_notes?: string | null;
  created_by?: string;
  updated_by?: string;
  updated_at?: string;
  created_at?: string;
}

export interface ReportWithLines extends Report {
  lines: ReportLine[];
}

export interface ReportCreate {
  budget_id: string;
  name: string;
  period_start?: string;
  period_end?: string;
}

export interface ReportUpdate {
  name?: string;
  period_start?: string | null;
  period_end?: string | null;
}

export interface ReportReviewRequest {
  decision: ReportStatus;
  review_notes?: string;
}

export interface ReportLine {
  id: string;
  report_id?: string;
  budget_line_id?: string;
  description?: string;
  amount?: number;
  // The real-world date the expense happened — distinct from created_at
  // (when the row was written).
  expense_date?: string; // ISO date string
  extra_fields?: Record<string, unknown> | null;
  created_by?: string;
  updated_by?: string;
  updated_at?: string;
  created_at?: string;
}

export interface ReportLineCreate {
  report_id: string;
  budget_line_id: string;
  description: string;
  amount: number;
  expense_date: string;
  extra_fields?: Record<string, unknown>;
}

export interface ReportLineUpdate {
  report_id: string;
  description?: string;
  amount?: number;
  expense_date?: string;
  extra_fields?: Record<string, unknown>;
}

export interface Attachment {
  id: string;
  report_line_id?: string;
  filename?: string;
  content_type?: string;
  size?: number;
  storage_key?: string;
  created_by?: string;
  updated_by?: string;
  updated_at?: string;
  created_at?: string;
}

export interface BudgetLinePreview {
  category_name: string;
  description: string;
  amount: number;
  extra_fields?: Record<string, unknown> | null;
}

export interface CreateBudgetWithLinesRequest {
  budget_name: string;
  external_funder_name: string;
  duration_months?: number | null;
  lines: BudgetLinePreview[];
}
