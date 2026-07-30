import React, { useState } from "react";

type ButtonProps = {
  children: React.ReactNode;
  onClick?: () => void;
  type?: "button" | "submit" | "reset";
  variant?:
    | "primary"
    | "secondary"
    | "danger"
    | "success"
    | "outline"
    | "ghost"
    | "icon"
    | "icon-danger"
    | "toggle"
    | "close"
    | "expander"
    | "simpleX"
    | "text";
  className?: string;
  active?: boolean;
  title?: string;
  disabled?: boolean;
};

export default function Button({
  children,
  onClick,
  type = "button",
  variant = "primary",
  className = "",
  active = false,
  title,
  disabled = false,
}: ButtonProps) {
  const baseStyles =
    "rounded-lg transition-all font-medium focus:outline-none focus:ring-2 disabled:opacity-40 disabled:cursor-not-allowed disabled:pointer-events-none";

  const variants: Record<string, string> = {
    primary:
      "bg-slate-700 text-white hover:bg-slate-800 focus:ring-slate-400 py-2 px-4",
    secondary:
      "bg-white border-2 border-slate-700 text-slate-700 hover:bg-slate-50 focus:ring-slate-400 py-2 px-4",
    outline:
      "border border-slate-300 text-slate-700 hover:bg-slate-50 focus:ring-slate-300 py-2 px-4",
    ghost: "text-slate-700 hover:bg-slate-100 focus:ring-slate-300 py-2 px-3",
    icon: "p-2 text-slate-700 hover:bg-slate-100 focus:ring-slate-300 rounded-lg",
    "icon-danger":
      "p-2 text-red-600 hover:bg-red-50 focus:ring-red-300 rounded-lg",
    toggle: active
      ? "p-2 rounded-lg bg-slate-700 text-white hover:bg-slate-800 focus:ring-slate-400"
      : "p-2 rounded-lg bg-white text-slate-700 border border-slate-300 hover:bg-slate-50 focus:ring-slate-300",
    close:
      "p-1 text-gray-500 hover:text-gray-800 hover:bg-gray-100 rounded focus:ring-gray-300",
    expander:
      "p-1 text-slate-700 hover:text-slate-900 hover:bg-slate-100 focus:ring-slate-300",
    danger:
      "bg-red-600 text-white hover:bg-red-700 focus:ring-red-300 py-2 px-4",
    success:
      "bg-green-600 text-white hover:bg-green-700 focus:ring-green-300 py-2 px-4",
    simpleX: "text-red-500 font-bold hover:text-red-700",
    text: "text-slate-700 hover:text-slate-900 font-medium",
  };

  return (
    <button
      type={type}
      onClick={onClick}
      title={title}
      disabled={disabled}
      className={`${baseStyles} ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

interface ConfirmDeleteButtonProps {
  onConfirm: () => void;
  className?: string;
  children?: React.ReactNode;
  variant?: "danger" | "icon-danger";
  title?: string;
  // Shown above the Yes/No pair — for confirmations with a consequence
  // beyond "delete this one thing" (e.g. cascading deletes) that's worth
  // spelling out before the user commits, not just implied by the button.
  confirmMessage?: string;
  disabled?: boolean;
}
export function ConfirmDeleteButton({
  onConfirm,
  className = "",
  children,
  variant = "danger",
  title,
  confirmMessage,
  disabled = false,
}: ConfirmDeleteButtonProps) {
  const [confirming, setConfirming] = useState(false);

  if (confirming) {
    return (
      <div className="flex items-center gap-2 flex-wrap">
        {confirmMessage && <span className="text-sm text-slate-600">{confirmMessage}</span>}
        <div className="flex items-center space-x-2">
          <Button
            variant="danger"
            onClick={() => {
              onConfirm();
              setConfirming(false);
            }}
            disabled={disabled}
            className="text-xs py-1 px-2"
          >
            Yes
          </Button>
          <Button
            variant="secondary"
            onClick={() => setConfirming(false)}
            disabled={disabled}
            className="text-xs py-1 px-2"
          >
            No
          </Button>
        </div>
      </div>
    );
  }

  return (
    <Button
      variant={variant}
      onClick={() => setConfirming(true)}
      className={className}
      title={title}
      disabled={disabled}
    >
      {children || "Delete"}
    </Button>
  );
}
