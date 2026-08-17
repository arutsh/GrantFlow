import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionHead } from "@/components/ui/SectionHead";
import { useAuth } from "@/context/AuthContext";
import { searchCustomers, Customer } from "@/api/customerApi";
import { impersonateCustomer } from "@/api/authApi";

// Superuser-only entry point into Company Management: picking a company
// starts an impersonation session (design.md decision 2 — no dedicated
// superuser-scoped endpoints for invite/remove/promote-demote/update-company,
// the picker's only job is to get the superuser an admin-scoped token for
// the target company, then this same page re-renders as the admin view).
export function CompanyPicker() {
  const { startImpersonation } = useAuth();
  const queryClient = useQueryClient();
  const [searchText, setSearchText] = useState("");

  const trimmedSearch = searchText.trim();
  const searchQuery = useQuery({
    queryKey: ["customers", "companyManagementSearch", trimmedSearch],
    queryFn: () => searchCustomers({ search: trimmedSearch }),
    enabled: trimmedSearch.length > 0,
  });

  const impersonateMutation = useMutation({
    mutationFn: (customer: Customer) => impersonateCustomer(customer.id),
    onSuccess: (data) => {
      startImpersonation(data.access_token, data.customer_name);
      queryClient.clear();
    },
  });

  const results = searchQuery.data ?? [];

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6 max-w-lg">
      <SectionHead title="Manage a company" hint="Superuser" />
      <p className="text-sm text-slate-500 mb-4">
        Search for a company to manage its users and details. You'll act as that
        company's admin for a short session.
      </p>
      <input
        autoFocus
        type="text"
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        placeholder="Search companies by name"
        className="border p-2 rounded w-full text-sm mb-3"
      />
      <div className="flex flex-col gap-1 max-h-80 overflow-auto">
        {searchQuery.isFetching && (
          <div className="text-xs text-slate-400 px-1 py-1">Searching...</div>
        )}
        {!searchQuery.isFetching && trimmedSearch.length > 0 && results.length === 0 && (
          <div className="text-xs text-slate-400 px-1 py-1">No matching companies.</div>
        )}
        {results.map((customer) => (
          <button
            key={customer.id}
            type="button"
            onClick={() => impersonateMutation.mutate(customer)}
            disabled={impersonateMutation.isPending}
            className="text-left px-3 py-2 rounded-lg hover:bg-slate-50 border border-transparent hover:border-slate-200 text-sm disabled:opacity-50"
          >
            <div className="font-medium text-slate-900 truncate">{customer.name}</div>
            <div className="text-xs text-slate-500">{customer.country}</div>
          </button>
        ))}
      </div>
      {impersonateMutation.isError && (
        <p className="text-xs text-red-500 mt-3">Failed to start managing this company.</p>
      )}
    </section>
  );
}
