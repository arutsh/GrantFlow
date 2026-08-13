export function ProgressBar({
  percent,
  className,
  fillClassName,
}: {
  percent: number;
  className?: string;
  fillClassName?: string;
}) {
  const clamped = Math.max(0, Math.min(100, percent));
  return (
    <div className={className ?? "h-1.5 rounded-full bg-slate-200 overflow-hidden"}>
      <div
        className={fillClassName ?? "h-full rounded-full bg-green-500"}
        style={{ width: `${clamped}%` }}
      />
    </div>
  );
}
