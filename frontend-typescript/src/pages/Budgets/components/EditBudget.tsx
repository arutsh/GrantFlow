import { editBudget } from "@/api/budgetApi";
import Button from "@/components/ui/Button";
import Modal from "@/components/ui/Modal";
import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useFunderPicker } from "@/hooks/useFunderPicker";
import { Budget } from "../types/budget";

export function EditBudgetModal({
  isOpen,
  onClose,
  data,
}: {
  isOpen: boolean;
  onClose: (updatedBudget: Budget | null) => void;
  data: Budget;
}) {
  const [budgetName, setBudgetName] = useState(data?.name || "");
  const [errorMessage, setErrorMessage] = useState("");

  const {
    donors,
    isPending: donorsPending,
    isError: donorsError,
    selectedDonorId,
    funderName,
    handleDonorChange,
    handleFunderNameChange,
    reset: resetFunderPicker,
    hasFunder,
  } = useFunderPicker(isOpen, {
    donorId: data?.funder?.id,
    donorName: data?.funder?.name,
  });

  useEffect(() => {
    if (data) {
      setBudgetName(data.name || "");
      resetFunderPicker({ donorId: data.funder?.id, donorName: data.funder?.name });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data]);

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
      editBudget(data.id, {
        name: budgetName,
        // Always sent (including cleared to "" when a donor is selected)
        // and funding_customer_id sent as explicit null when unset — same
        // "full metadata every save, mutually exclusive" convention as
        // AddBudgetModal/BudgetViewHeader, so this modal can't silently
        // leave both fields set on a donor-linked budget.
        external_funder_name: selectedDonorId ? "" : funderName,
        funding_customer_id: selectedDonorId || null,
      }),

    onSuccess: (updatedBudget) => {
      setErrorMessage("");
      onClose(updatedBudget);
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
    <Modal isOpen={isOpen} onClose={() => onClose(null)} title="New Budget">
      {errorMessage && <p className="text-red-500">{errorMessage}</p>}
      {data && (
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
      )}
    </Modal>
  );
}
