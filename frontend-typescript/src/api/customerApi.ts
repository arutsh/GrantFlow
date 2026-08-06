import gatewayApi from "@/api/gatewayApi";

export interface Customer {
  id: string;
  name: string;
  country: string;
  is_ngo: boolean;
  is_donor: boolean;
  currency: string;
}

export const searchCustomers = async (params: {
  is_ngo?: boolean;
  search?: string;
}): Promise<Customer[]> => {
  const { data } = await gatewayApi.get("/customers/", { params });
  return data;
};

// Batch name/detail lookup for a known set of ids — used to resolve
// donor-grantee rows (which only carry ids) into displayable customers,
// without an N+1 GET per row.
export const getCustomersByIds = async (customerIds: string[]): Promise<Customer[]> => {
  if (customerIds.length === 0) return [];
  const { data } = await gatewayApi.post("/customers/by_ids/", customerIds);
  return data;
};
