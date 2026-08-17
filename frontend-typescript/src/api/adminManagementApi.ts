import gatewayApi from "@/api/gatewayApi";

export interface CompanyUser {
  id: string;
  first_name: string | null;
  last_name: string | null;
  email: string;
  role: "superuser" | "admin" | "user";
  status: "active" | "pending" | "disabled";
  email_verified: boolean;
}

// Superuser (not impersonating) gets every user; an admin — real, or a
// superuser impersonating — gets only their own company's, per
// services/users/app/api/user_routes.py's list_users_endpoint.
export const listCompanyUsers = async (): Promise<CompanyUser[]> => {
  const { data } = await gatewayApi.get("/users/");
  return data;
};

export interface InviteUserPayload {
  email: string;
  first_name?: string;
  last_name?: string;
  role?: "admin" | "user";
}

export interface InviteUserResponse {
  user_id: string;
  email: string;
  status: string;
}

export const inviteUser = async (payload: InviteUserPayload): Promise<InviteUserResponse> => {
  const { data } = await gatewayApi.post("/users/invite", payload);
  return data;
};

export const removeCompanyUser = async (userId: string): Promise<void> => {
  await gatewayApi.delete(`/users/${userId}/remove`);
};

export const updateUserRole = async (
  userId: string,
  role: "admin" | "user",
): Promise<CompanyUser> => {
  const { data } = await gatewayApi.patch(`/users/${userId}/role`, { role });
  return data;
};

export const acceptInvite = async (
  email: string,
  token: string,
  password: string,
): Promise<{ email_verified: boolean }> => {
  const { data } = await gatewayApi.post("/users/accept-invite", { email, token, password });
  return data;
};
