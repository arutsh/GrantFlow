import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { listDonorGrantees } from "@/api/donorGranteeApi";
import { getCustomersByIds, Customer } from "@/api/customerApi";

export interface FunderSelection {
  donorId?: string;
  donorName?: string;
}

// Shared by AddBudgetModal, BudgetViewHeader, and EditBudgetModal — the
// grantee's approved-donor-or-custom-name picker, including the two-query
// (donor-grantee list -> batch customer resolution) fetch those three used
// to duplicate independently.
export function useFunderPicker(enabled: boolean, initial: FunderSelection) {
  const [selectedDonorId, setSelectedDonorId] = useState(initial.donorId ?? "");
  const [funderName, setFunderName] = useState(initial.donorId ? "" : initial.donorName ?? "");

  const donorGranteesQuery = useQuery({
    queryKey: ["donorGrantees", "grantee"],
    queryFn: () => listDonorGrantees("grantee"),
    enabled,
  });
  const donorIds = (donorGranteesQuery.data ?? []).map((dg) => dg.donor_id);
  const donorCustomersQuery = useQuery({
    queryKey: ["customers", "byIds", donorIds],
    queryFn: () => getCustomersByIds(donorIds),
    enabled: enabled && donorIds.length > 0,
  });

  const fetchedDonors = donorCustomersQuery.data ?? [];
  // The budget's current donor is always offered as a selectable option,
  // even if the live approved-donor list no longer includes them (e.g. the
  // relationship was revoked after this budget was already linked) —
  // otherwise the <select> would silently render blank while state still
  // held the stale id, and an unrelated save would resubmit it, surfacing
  // as a confusing rejection from the backend's relationship check instead
  // of a clear "this donor is no longer approved" signal.
  const donors: Customer[] =
    initial.donorId && !fetchedDonors.some((d) => d.id === initial.donorId)
      ? [
          ...fetchedDonors,
          {
            id: initial.donorId,
            name: initial.donorName || "Unknown donor",
            country: "",
            is_ngo: false,
            is_donor: true,
            currency: "",
          },
        ]
      : fetchedDonors;

  // Pending only while waiting on data that's actually needed — the
  // customer-batch query never runs (and so never counts) when there are no
  // donor ids to resolve.
  const isPending =
    enabled && (donorGranteesQuery.isPending || (donorIds.length > 0 && donorCustomersQuery.isPending));
  const isError = donorGranteesQuery.isError || donorCustomersQuery.isError;

  const handleDonorChange = (id: string) => {
    setSelectedDonorId(id);
    if (id) setFunderName("");
  };
  const handleFunderNameChange = (name: string) => {
    setFunderName(name);
    if (name) setSelectedDonorId("");
  };
  const reset = (next: FunderSelection) => {
    setSelectedDonorId(next.donorId ?? "");
    setFunderName(next.donorId ? "" : next.donorName ?? "");
  };

  // Mirrors the backend's either/or requirement (BudgetCreate.check_funder /
  // update_budget_service's funder_touched guard) — a budget must always
  // have a donor or a funder name, never neither.
  const hasFunder = !!selectedDonorId || !!funderName.trim();

  return {
    donors,
    isPending,
    isError,
    selectedDonorId,
    funderName,
    handleDonorChange,
    handleFunderNameChange,
    reset,
    hasFunder,
  };
}
