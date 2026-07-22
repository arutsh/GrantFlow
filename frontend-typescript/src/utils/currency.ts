export function formatCurrency(amount: number, currencyCode?: string): string {
  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency: currencyCode || "GBP",
    maximumFractionDigits: 0,
  }).format(amount);
}

// A donor can fund budgets in more than one currency, so totals must not be
// blended into a single number under one currency — render each currency's
// total separately instead.
export function formatCurrencyAmounts(
  amounts: { currency?: string; total_allocated: number }[],
): string {
  if (amounts.length === 0) return formatCurrency(0);
  return amounts
    .map((a) => formatCurrency(a.total_allocated, a.currency))
    .join(" + ");
}
