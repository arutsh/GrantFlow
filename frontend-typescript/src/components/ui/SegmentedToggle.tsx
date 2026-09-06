import { ReactNode } from "react";

type SegmentedToggleOption<T extends string> = {
  value: T;
  label: string;
  icon: ReactNode;
  title?: string;
};

// Joined sliding-thumb toggle for structural controls, distinct from Button's pill "toggle" variant.
export function SegmentedToggle<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
  className = "",
}: {
  value: T;
  options: readonly [SegmentedToggleOption<T>, SegmentedToggleOption<T>];
  onChange: (value: T) => void;
  ariaLabel: string;
  className?: string;
}) {
  return (
    <div
      role="group"
      aria-label={ariaLabel}
      className={`relative inline-flex gap-0.5 rounded-lg border border-slate-200 bg-slate-100 p-[3px] ${className}`}
    >
      <span
        className="absolute inset-y-[3px] left-[3px] w-[calc(50%-4px)] rounded-md bg-teal-700 transition-transform duration-200 ease-out"
        style={{
          transform: value === options[1].value ? "translateX(calc(100% + 2px))" : undefined,
        }}
      />
      {options.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => onChange(option.value)}
          title={option.title ?? option.label}
          className={`relative z-10 flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
            option.value === value ? "text-white" : "text-slate-500 hover:text-slate-700"
          }`}
        >
          {option.icon}
          {option.label}
        </button>
      ))}
    </div>
  );
}
