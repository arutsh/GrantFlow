import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { importBudgetFromExcel } from "@/api/budgetApi";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { Budget } from "../types/budget";

// Kept in sync by hand with the backend's MAX_IMPORT_SIZE — drift here only
// means a slightly wrong client-side error message, the backend stays
// authoritative (same convention as AttachmentUpload.tsx's own limit).
const MAX_SIZE_BYTES = 10 * 1024 * 1024;
const ACCEPT_ATTR =
  ".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

// Advances on a timer, not real progress — the backend call has no progress events.
const STATUS_MESSAGES = [
  "Uploading your file…",
  "Reading your spreadsheet…",
  "Finding the budget lines…",
  "Extracting amounts and categories…",
  "Double-checking the currencies…",
  "Still crunching the numbers…",
  "Good spreadsheets take a little patience…",
  "Almost there…",
];
const STATUS_INTERVAL_MS = 2500;

function isXlsxFile(file: File): boolean {
  return file.name.toLowerCase().endsWith(".xlsx");
}

export function ImportExcelModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: (importedBudget: Budget | null) => void;
}) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState("");
  const [statusIndex, setStatusIndex] = useState(0);

  const mutation = useMutation({
    mutationFn: importBudgetFromExcel,
    onSuccess: (budget) => {
      setError("");
      onClose(budget);
    },
    onError: (err) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data
        ?.detail;
      setError(detail || "Failed to import the spreadsheet. Please try again.");
    },
  });

  useEffect(() => {
    if (!mutation.isPending) {
      setStatusIndex(0);
      return;
    }
    const interval = setInterval(() => {
      setStatusIndex((i) => Math.min(i + 1, STATUS_MESSAGES.length - 1));
    }, STATUS_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [mutation.isPending]);

  const validateAndUpload = (file: File) => {
    setError("");
    if (!isXlsxFile(file)) {
      setError("Only .xlsx files are supported.");
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      setError("File exceeds the 10MB limit.");
      return;
    }
    mutation.mutate(file);
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (fileInputRef.current) fileInputRef.current.value = "";
    if (file) validateAndUpload(file);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (mutation.isPending) return;
    const file = e.dataTransfer.files?.[0];
    if (file) validateAndUpload(file);
  };

  return (
    <Modal isOpen={isOpen} onClose={() => onClose(null)} title="Import from Excel">
      <div className="flex flex-col gap-3">
        <p className="text-sm text-gray-600">
          Upload your organization's existing Excel budget. We'll read it and create a
          draft budget for you to review and confirm.
        </p>
        <div
          onDragOver={(e) => {
            e.preventDefault();
            if (!mutation.isPending) setIsDragging(true);
          }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-lg p-6 text-center text-sm transition-colors ${
            isDragging ? "border-slate-500 bg-slate-50" : "border-slate-300"
          }`}
        >
          {mutation.isPending ? (
            <div className="flex flex-col items-center gap-2 py-2" aria-live="polite">
              <div className="w-5 h-5 border-2 border-slate-300 border-t-slate-600 rounded-full animate-spin" />
              <p className="text-slate-600">{STATUS_MESSAGES[statusIndex]}</p>
            </div>
          ) : (
            <>
              <p className="text-slate-500 mb-2">Drag & drop your .xlsx file here, or</p>
              <input
                ref={fileInputRef}
                type="file"
                aria-label="Import budget from Excel"
                accept={ACCEPT_ATTR}
                onChange={handleFileChange}
                className="text-xs text-slate-600"
              />
            </>
          )}
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <div className="flex justify-end">
          <Button variant="secondary" onClick={() => onClose(null)}>
            Cancel
          </Button>
        </div>
      </div>
    </Modal>
  );
}
