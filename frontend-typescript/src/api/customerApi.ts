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

export const getCustomer = async (customerId: string): Promise<Customer> => {
  const { data } = await gatewayApi.get(`/customers/${customerId}`);
  return data;
};

export interface CompanyUpdatePayload {
  name?: string;
  country?: string;
  currency?: string;
  is_ngo?: boolean;
  is_donor?: boolean;
}

export const updateCustomer = async (
  customerId: string,
  updates: CompanyUpdatePayload,
): Promise<Customer> => {
  const { data } = await gatewayApi.patch(`/customers/${customerId}`, updates);
  return data;
};

export const deactivateCustomer = async (customerId: string): Promise<Customer> => {
  const { data } = await gatewayApi.post(`/customers/${customerId}/deactivate`);
  return data;
};
