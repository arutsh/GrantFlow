import { Link } from "react-router-dom";
import type { ReactNode } from "react";

// A button-styled Link — Button.tsx renders a real <button> so it can't be
// used for navigation. Deliberately smaller than Button's default sizing
// (text-xs, tighter padding) so a row of two or three of these in a table
// action column or a mobile card doesn't wrap onto a second line.
export function LinkButton({
  to,
  children,
  className = "",
}: {
  to: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Link
      to={to}
      className={`inline-flex items-center justify-center gap-1 whitespace-nowrap rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-300 font-medium text-xs py-1.5 px-2.5 transition-colors ${className}`}
    >
      {children}
    </Link>
  );
}
