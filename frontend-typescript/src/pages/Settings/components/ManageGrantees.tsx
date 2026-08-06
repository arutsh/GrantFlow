import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionHead } from "@/components/ui/SectionHead";
import Button from "@/components/ui/Button";
import { listDonorGrantees, createDonorGrantee, deleteDonorGrantee } from "@/api/donorGranteeApi";
import { searchCustomers, getCustomersByIds, Customer } from "@/api/customerApi";

// Cycled deterministically per grantee row, same convention as
// DonorDashboard's GranteeCard avatars.
const AVATAR_COLORS = [
  "bg-slate-700",
  "bg-teal-600",
  "bg-amber-500",
  "bg-indigo-500",
  "bg-rose-500",
  "bg-cyan-600",
];

function initials(name?: string): string {
  if (!name) return "—";
  const parts = name.trim().split(/\s+/).slice(0, 2);
  return parts.map((p) => p[0]?.toUpperCase() ?? "").join("") || "—";
}

function GranteeApprovalCard({
  customer,
  colorClass,
  onRevoke,
  isRevoking,
}: {
  customer: Customer | undefined;
  colorClass: string;
  onRevoke: () => void;
  isRevoking: boolean;
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3 min-w-0">
        <div
          className={`w-9 h-9 rounded-lg flex items-center justify-center text-white font-bold text-xs flex-shrink-0 ${colorClass}`}
        >
          {initials(customer?.name)}
        </div>
        <div className="min-w-0">
          <div className="font-semibold text-sm text-slate-900 truncate">
            {customer?.name ?? "—"}
          </div>
          <div className="text-xs text-slate-500">{customer?.country ?? "—"}</div>
        </div>
      </div>
      <Button variant="danger" onClick={onRevoke} disabled={isRevoking}>
        Revoke
      </Button>
    </div>
  );
}

// Donor-only section on the Settings page — a donor customer can search NGO
// customers by name, approve them as a grantee, and revoke an existing
// approval. Gated by `isDonor` in SettingsPage itself.
export function ManageGrantees() {
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState("");

  const approvedQuery = useQuery({
    queryKey: ["donorGrantees", "donor"],
    queryFn: () => listDonorGrantees("donor"),
  });
  const approved = approvedQuery.data ?? [];
  const approvedGranteeIds = approved.map((dg) => dg.grantee_id);

  // Donor-grantee rows only carry ids — resolve them to displayable
  // customers in one batch call rather than a GET per row.
  const approvedCustomersQuery = useQuery({
    queryKey: ["customers", "byIds", approvedGranteeIds],
    queryFn: () => getCustomersByIds(approvedGranteeIds),
    enabled: approvedGranteeIds.length > 0,
  });
  const customersById = new Map((approvedCustomersQuery.data ?? []).map((c) => [c.id, c]));

  const searchMutation = useMutation({
    mutationFn: (search: string) => searchCustomers({ is_ngo: true, search }),
  });

  const addMutation = useMutation({
    mutationFn: (granteeId: string) => createDonorGrantee(granteeId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["donorGrantees", "donor"] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (id: string) => deleteDonorGrantee(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["donorGrantees", "donor"] });
    },
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchText.trim()) return;
    searchMutation.mutate(searchText.trim());
  };

  const searchResults = (searchMutation.data ?? []).filter(
    (c) => !approvedGranteeIds.includes(c.id),
  );

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Manage Grantees" hint={`${approved.length} approved`} />

      <form onSubmit={handleSearch} className="flex gap-2 mb-4">
        <input
          type="text"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Search NGOs by name"
          className="border p-2 rounded w-full max-w-sm"
        />
        <Button type="submit" variant="secondary" disabled={searchMutation.isPending}>
          Search
        </Button>
      </form>

      {searchMutation.isSuccess && (
        <div className="mb-6 flex flex-col gap-2">
          {searchResults.length === 0 ? (
            <div className="text-sm text-slate-500">No matching NGOs to add.</div>
          ) : (
            searchResults.map((customer) => (
              <div
                key={customer.id}
                className="bg-white rounded-xl border border-slate-200 shadow-sm p-3 flex items-center justify-between gap-3"
              >
                <div className="min-w-0">
                  <div className="font-semibold text-sm text-slate-900 truncate">
                    {customer.name}
                  </div>
                  <div className="text-xs text-slate-500">{customer.country}</div>
                </div>
                <Button
                  variant="primary"
                  onClick={() => addMutation.mutate(customer.id)}
                  disabled={addMutation.isPending}
                >
                  Add
                </Button>
              </div>
            ))
          )}
        </div>
      )}

      {approvedQuery.isPending ? (
        <div className="text-sm text-slate-500">Loading...</div>
      ) : approvedQuery.isError ? (
        <div className="text-sm text-red-500">Error loading approved grantees.</div>
      ) : approved.length === 0 ? (
        <div className="flex items-center justify-center py-10 bg-white rounded-lg border border-slate-200">
          <div className="text-center">
            <p className="text-sm font-semibold text-slate-900 mb-1">No approved grantees yet</p>
            <p className="text-xs text-slate-500">
              Search for an NGO above to approve them as a grantee.
            </p>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {approved.map((dg, i) => (
            <GranteeApprovalCard
              key={dg.id}
              customer={customersById.get(dg.grantee_id)}
              colorClass={AVATAR_COLORS[i % AVATAR_COLORS.length]}
              onRevoke={() => revokeMutation.mutate(dg.id)}
              isRevoking={revokeMutation.isPending && revokeMutation.variables === dg.id}
            />
          ))}
        </div>
      )}
    </section>
  );
}
