import gatewayApi from "@/api/gatewayApi";

export interface ImpersonateResponse {
  access_token: string;
  token_type: string;
  customer_id: string;
  customer_name: string;
  expires_in: number;
}

export const impersonateCustomer = async (customerId: string): Promise<ImpersonateResponse> => {
  const { data } = await gatewayApi.post("/auth/impersonate", { customer_id: customerId });
  return data;
};
