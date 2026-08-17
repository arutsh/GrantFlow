import React, { forwardRef } from "react";

interface InputProps {
  label?: string;
  name: string;
  type?: string;
  value: any;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  required?: boolean;
  placeholder?: string;
  showLabel?: boolean;
  disabled?: boolean;
  errorMsg?: string | null;
  min?: string | number;
  max?: string | number;
  // Rendered inside the input's own relative wrapper, absolutely positioned
  // on the right — e.g. PasswordInput's show/hide toggle.
  rightElement?: React.ReactNode;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  (
    {
      label = "",
      name,
      type = "text",
      value,
      onChange,
      required = false,
      placeholder,
      showLabel = true,
      disabled = false,
      errorMsg = null,
      min,
      max,
      rightElement,
    },
    ref
  ) => {
    return (
      <div className="mb-4">
        {showLabel && (
          <label
            htmlFor={name}
            className="block text-sm font-medium text-gray-700 mb-1"
          >
            {label} {required && <span className="text-red-500">*</span>}
          </label>
        )}
        <div className="relative">
          <input
            ref={ref}
            id={name}
            name={name}
            type={type}
            value={value}
            onChange={onChange}
            required={required}
            placeholder={placeholder}
            disabled={disabled}
            min={min}
            max={max}
            className={`w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-brand-blue focus:border-brand-blue sm:text-sm ${
              rightElement ? "pr-10" : ""
            } ${errorMsg ? "border-red-500" : "border-gray-300"}`}
          />
          {rightElement && (
            <div className="absolute inset-y-0 right-0 flex items-center pr-3">
              {rightElement}
            </div>
          )}
        </div>
        {errorMsg && (
          <div className="text-red-500 text-xs px-1 py-1">{errorMsg}</div>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
export default Input;
