import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { UserCog } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { searchCustomers, Customer } from "@/api/customerApi";
import { impersonateCustomer } from "@/api/authApi";

// Superuser-only customer search, rendered in TopBar to the left of the
// user menu. Selecting a result mints an impersonation token and swaps the
// app's active session to it — the query cache is cleared on success since
// it's keyed without customer_id and would otherwise leak the previous
// session's cached data into the impersonated view.
export function ImpersonatePicker() {
  const { startImpersonation } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const trimmedSearch = searchText.trim();
  const searchQuery = useQuery({
    queryKey: ["customers", "impersonateSearch", trimmedSearch],
    queryFn: () => searchCustomers({ search: trimmedSearch }),
    enabled: isOpen && trimmedSearch.length > 0,
  });

  const impersonateMutation = useMutation({
    mutationFn: (customer: Customer) => impersonateCustomer(customer.id),
    onSuccess: (data) => {
      startImpersonation(data.access_token, data.customer_name);
      queryClient.clear();
      setIsOpen(false);
      setSearchText("");
      navigate("/dashboard");
    },
  });

  const results = searchQuery.data ?? [];

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        aria-label="Impersonate a customer"
        title="Impersonate a customer"
        className="flex items-center justify-center w-9 h-9 rounded-lg text-slate-600 hover:bg-slate-100 transition-colors"
      >
        <UserCog size={20} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 bg-white border border-slate-200 rounded-xl shadow-lg p-3 z-30">
          <p className="text-xs font-semibold text-slate-500 mb-2">Impersonate customer</p>
          <input
            autoFocus
            type="text"
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            placeholder="Search customers by name"
            className="border p-2 rounded w-full text-sm"
          />
          <div className="mt-2 max-h-64 overflow-auto flex flex-col gap-1">
            {searchQuery.isFetching && (
              <div className="text-xs text-slate-400 px-1 py-1">Searching...</div>
            )}
            {!searchQuery.isFetching && trimmedSearch.length > 0 && results.length === 0 && (
              <div className="text-xs text-slate-400 px-1 py-1">No matching customers.</div>
            )}
            {results.map((customer) => (
              <button
                key={customer.id}
                type="button"
                onClick={() => impersonateMutation.mutate(customer)}
                disabled={impersonateMutation.isPending}
                className="text-left px-2 py-1.5 rounded-lg hover:bg-slate-50 text-sm disabled:opacity-50"
              >
                <div className="font-medium text-slate-900 truncate">{customer.name}</div>
                <div className="text-xs text-slate-500">{customer.country}</div>
              </button>
            ))}
          </div>
          {impersonateMutation.isError && (
            <p className="text-xs text-red-500 mt-2">Failed to start impersonation.</p>
          )}
        </div>
      )}
    </div>
  );
}
