import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { SectionHead } from "@/components/ui/SectionHead";
import Button from "@/components/ui/Button";
import Input from "@/components/ui/Input";
import { getCustomer, updateCustomer, CompanyUpdatePayload } from "@/api/customerApi";

export function CompanyDetailsForm({ customerId }: { customerId: string }) {
  const queryClient = useQueryClient();
  const companyQuery = useQuery({
    queryKey: ["customers", customerId],
    queryFn: () => getCustomer(customerId),
  });

  const [form, setForm] = useState<CompanyUpdatePayload>({});

  useEffect(() => {
    if (companyQuery.data) {
      setForm({
        name: companyQuery.data.name,
        country: companyQuery.data.country,
        currency: companyQuery.data.currency,
        is_ngo: companyQuery.data.is_ngo,
        is_donor: companyQuery.data.is_donor,
      });
    }
  }, [companyQuery.data]);

  const updateMutation = useMutation({
    mutationFn: () => updateCustomer(customerId, form),
    onSuccess: (data) => {
      queryClient.setQueryData(["customers", customerId], data);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate();
  };

  if (companyQuery.isPending) {
    return (
      <section className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="text-sm text-slate-500">Loading company details...</div>
      </section>
    );
  }

  return (
    <section className="bg-white rounded-xl border border-gray-200 p-6">
      <SectionHead title="Company details" />
      <form onSubmit={handleSubmit} className="flex flex-col gap-1 max-w-sm">
        <Input
          label="Name"
          name="name"
          value={form.name ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
          required
        />
        <Input
          label="Country (ISO Alpha-2)"
          name="country"
          value={form.country ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, country: e.target.value.toUpperCase() }))}
          required
        />
        <Input
          label="Currency"
          name="currency"
          value={form.currency ?? ""}
          onChange={(e) => setForm((f) => ({ ...f, currency: e.target.value.toUpperCase() }))}
          required
        />
        <div className="flex flex-col gap-2 mb-4 mt-2">
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={!!form.is_ngo}
              onChange={(e) => setForm((f) => ({ ...f, is_ngo: e.target.checked }))}
            />
            This company is a grantee (NGO)
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={!!form.is_donor}
              onChange={(e) => setForm((f) => ({ ...f, is_donor: e.target.checked }))}
            />
            This company is a donor
          </label>
        </div>
        <Button type="submit" variant="primary" disabled={updateMutation.isPending}>
          Save changes
        </Button>
        {updateMutation.isSuccess && (
          <p className="text-xs text-green-600 mt-2">Saved.</p>
        )}
        {updateMutation.isError && (
          <p className="text-xs text-red-500 mt-2">Failed to save company details.</p>
        )}
      </form>
    </section>
  );
}
