import { getUserIdFromToken } from "@/utils/token";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import gatewayApi from "./gatewayApi";

export const loginUser = async (email: string, password: string) => {
  const { data } = await gatewayApi.post("/auth/login", { email, password });
  return data;
};

export const registerUser = async (email: string, password: string) => {
  const { data } = await gatewayApi.post("/register", { email, password });
  return data;
};

export const verifyEmail = async (email: string, token: string) => {
  const { data } = await gatewayApi.post("/auth/verify-email", { email, token });
  return data;
};

export const resendVerification = async () => {
  const { data } = await gatewayApi.post("/auth/resend-verification", {});
  return data;
};

export const userOnboarding = async (
  first_name: string,
  last_name: string,
  customer_name: string,
  user_id: string | null
) => {
  
    const { data } = await gatewayApi.patch(`/users/${user_id}/`, {
    first_name: first_name,
    last_name: last_name,
    new_customer_name: customer_name
  });
  return data;
}
