import moment from "moment";


/**
 * Convert UTC datetime string to local datetime string
 * @param utcDate - UTC datetime string (ISO format)
 * @param format - Optional display format, e.g., "YYYY-MM-DD HH:mm"
 * @returns Local datetime string
 */
export function utcToLocal(utcDate: string | null | undefined, format: string = "YYYY-MM-DD HH:mm") {
  if (!utcDate) return "N/A";
  const m = moment.utc(utcDate);
  if (!m.isValid()) return "N/A";
  return m.local().format(format);
}

/**
 * Format a date-only string (e.g. Budget.start_date, "YYYY-MM-DD") for display.
 * Returns null (not a placeholder string) when unset, so callers decide the
 * omitted-value copy themselves.
 */
export function formatDateOnly(
  dateStr: string | null | undefined,
  format: string = "DD MMM YYYY",
): string | null {
  if (!dateStr) return null;
  const m = moment(dateStr);
  return m.isValid() ? m.format(format) : null;
}
