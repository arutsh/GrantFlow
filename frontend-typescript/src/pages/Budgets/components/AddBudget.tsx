import { createBudget } from "@/api/budgetApi";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { useMutation } from "@tanstack/react-query";
import { useFunderPicker } from "@/hooks/useFunderPicker";

import { useState } from "react";
import { Budget } from "../types/budget";

export function AddBudgetModal({
  isOpen,
  onClose,
}: {
  isOpen: boolean;
  onClose: (updatedBudget: Budget | null) => void;
}) {
  const [budgetName, setBudgetName] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  // Only fetched while the modal is actually open, matching
  // CurrencyLedgerPanel's enabled-gating convention. No existing funder to
  // seed from — every field starts blank for a brand-new budget.
  const {
    donors,
    isPending: donorsPending,
    isError: donorsError,
    selectedDonorId,
    funderName,
    handleDonorChange,
    handleFunderNameChange,
    hasFunder,
  } = useFunderPicker(isOpen, {});

  const mutation = useMutation({
    mutationFn: ({
      budgetName,
      funderName,
      selectedDonorId,
    }: {
      budgetName: string;
      funderName: string;
      selectedDonorId: string;
    }) =>
      createBudget({
        name: budgetName,
        external_funder_name: selectedDonorId ? undefined : funderName || undefined,
        funding_customer_id: selectedDonorId || undefined,
      }),

    onSuccess: (newBudget) => {
      setErrorMessage("");
      onClose(newBudget);
    },
    onError: () => {
      setErrorMessage("Failed to update budget");
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      budgetName,
      funderName,
      selectedDonorId,
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={() => onClose(null)} title="Add Budget">
      {errorMessage && <p className="text-red-500">{errorMessage}</p>}
      <form onSubmit={handleSubmit} className="flex flex-col space-y-4">
        <input
          type="text"
          value={budgetName}
          onChange={(e) => setBudgetName(e.target.value)}
          placeholder="Budget Name"
          className="border p-2 rounded w-full"
        />
        {donors.length > 0 ? (
          <select
            aria-label="Donor"
            value={selectedDonorId}
            onChange={(e) => handleDonorChange(e.target.value)}
            className="border p-2 rounded w-full"
          >
            <option value="">Select a donor (optional)</option>
            {donors.map((donor) => (
              <option key={donor.id} value={donor.id}>
                {donor.name}
              </option>
            ))}
          </select>
        ) : (
          !donorsPending && (
            <p className="text-sm text-gray-500">
              {donorsError
                ? "Failed to load your approved donors — try reopening this form."
                : "No approved donors yet — ask a donor to add you before selecting them here."}
            </p>
          )
        )}
        <input
          type="text"
          value={funderName}
          onChange={(e) => handleFunderNameChange(e.target.value)}
          placeholder="Funder name"
          disabled={!!selectedDonorId}
          className="border p-2 rounded w-full disabled:bg-gray-100"
        />
        {!hasFunder && (
          <p className="text-sm text-red-500">
            Select a donor or enter a funder name to continue.
          </p>
        )}
        <div className="flex justify-end space-x-2">
          <Button type="submit" disabled={!hasFunder}>
            Save
          </Button>
          <Button variant="secondary" onClick={() => onClose(null)}>
            Cancel
          </Button>
        </div>
      </form>
    </Modal>
  );
}
