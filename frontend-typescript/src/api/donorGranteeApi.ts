import gatewayApi from "@/api/gatewayApi";

export interface DonorGrantee {
  id: string;
  donor_id: string;
  grantee_id: string;
}

export const listDonorGrantees = async (
  requestType: "donor" | "grantee"
): Promise<DonorGrantee[]> => {
  const { data } = await gatewayApi.get("/donor-grantees/", {
    params: { request_type: requestType },
  });
  return data;
};

export const createDonorGrantee = async (granteeId: string): Promise<DonorGrantee> => {
  const { data } = await gatewayApi.post("/donor-grantees/", { grantee_id: granteeId });
  return data;
};

export const deleteDonorGrantee = async (id: string): Promise<void> => {
  await gatewayApi.delete(`/donor-grantees/${id}`);
};
