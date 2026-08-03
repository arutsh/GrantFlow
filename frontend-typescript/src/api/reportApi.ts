import gatewayApi from "@/api/gatewayApi";
import {
  Report,
  ReportWithLines,
  ReportWithBudgetInfo,
  ReportCreate,
  ReportUpdate,
  ReportReviewRequest,
  ReportLine,
  ReportLineCreate,
  ReportLineUpdate,
  Attachment,
} from "@/pages/Budgets/types/budget";

// Reports

export const createReport = async (report: ReportCreate): Promise<Report> => {
  const { data } = await gatewayApi.post("/reports/", report);
  return data;
};

export const listReportsByBudget = async (
  budgetId: string
): Promise<Report[]> => {
  const { data } = await gatewayApi.get(`/reports/by-budget/${budgetId}`);
  return data;
};

// Owner's cross-budget reports directory — every report on a budget this
// customer owns, joined with parent-budget name/status/funder. Unfiltered
// (no args) so the directory page can derive its own filter dropdown
// options and filter client-side, matching budgets.tsx's convention at this
// data scale.
export const listAllReports = async (): Promise<ReportWithBudgetInfo[]> => {
  const { data } = await gatewayApi.get("/reports/");
  return data;
};

// Donor's cross-budget reports directory — each grantee's reports against
// the budgets this donor funds, joined with parent-budget name/status/
// owner. The funder-side counterpart to listAllReports, same unfiltered/
// client-filtered convention.
export const listFundedReports = async (): Promise<ReportWithBudgetInfo[]> => {
  const { data } = await gatewayApi.get("/reports/funded/");
  return data;
};

export const getReport = async (id: string): Promise<ReportWithLines> => {
  const { data } = await gatewayApi.get(`/reports/${id}`);
  return data;
};

export const updateReport = async (
  id: string,
  report: ReportUpdate
): Promise<Report> => {
  const { data } = await gatewayApi.patch(`/reports/${id}`, report);
  return data;
};

export const deleteReport = async (id: string) => {
  const { data } = await gatewayApi.delete(`/reports/${id}`);
  return data;
};

export const submitReport = async (id: string): Promise<Report> => {
  const { data } = await gatewayApi.post(`/reports/${id}/submit`, {});
  return data;
};

export const reviewReport = async (
  id: string,
  review: ReportReviewRequest
): Promise<Report> => {
  const { data } = await gatewayApi.post(`/reports/${id}/review`, review);
  return data;
};

export const reopenReport = async (id: string): Promise<Report> => {
  const { data } = await gatewayApi.post(`/reports/${id}/reopen`, {});
  return data;
};

// Report lines

export const createReportLine = async (
  line: ReportLineCreate
): Promise<ReportLine> => {
  const { data } = await gatewayApi.post("/report-lines/", line);
  return data;
};

export const listReportLinesByReport = async (
  reportId: string
): Promise<ReportLine[]> => {
  const { data } = await gatewayApi.get(`/report-lines/by-report/${reportId}`);
  return data;
};

export const updateReportLine = async (
  id: string,
  line: ReportLineUpdate
): Promise<ReportLine> => {
  const { data } = await gatewayApi.patch(`/report-lines/${id}`, line);
  return data;
};

export const deleteReportLine = async (id: string) => {
  const { data } = await gatewayApi.delete(`/report-lines/${id}`);
  return data;
};

// Attachments

export const uploadAttachment = async (
  reportLineId: string,
  file: File
): Promise<Attachment> => {
  const formData = new FormData();
  formData.append("report_line_id", reportLineId);
  formData.append("file", file);
  const { data } = await gatewayApi.post("/attachments/", formData);
  return data;
};

export const listAttachmentsByReportLine = async (
  reportLineId: string
): Promise<Attachment[]> => {
  const { data } = await gatewayApi.get(
    `/attachments/by-report-line/${reportLineId}`
  );
  return data;
};

// Hits the presigned-URL redirect (#157) rather than streaming through the
// app: the gateway 307s to a short-lived direct-to-storage URL (the browser
// drops our Authorization header on that hop, which is fine — the presigned
// URL carries its own signature), and Content-Disposition still triggers the
// filename-correct download. Requires the storage bucket's CORS policy to
// allow this origin, since the blob is ultimately read from a different
// origin (S3/MinIO) than the gateway.
export const downloadAttachment = async (
  id: string,
  filename: string
): Promise<void> => {
  const { data } = await gatewayApi.get(`/attachments/${id}/download-url`, {
    responseType: "blob",
  });
  const url = window.URL.createObjectURL(data);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
};

export const deleteAttachment = async (id: string) => {
  const { data } = await gatewayApi.delete(`/attachments/${id}`);
  return data;
};
