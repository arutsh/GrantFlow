import axios, { AxiosInstance, AxiosError } from "axios";
import { notifyTokenRefreshed } from "@/utils/tokenRefreshBridge";

export const getAuthToken = (): string | null => {
  return localStorage.getItem("token") || sessionStorage.getItem("token");
};

export const getRefreshToken = () =>
  localStorage.getItem("refreshToken") ||
  sessionStorage.getItem("refreshToken");

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

const subscribeTokenRefresh = (cb: (token: string) => void) => {
  refreshSubscribers.push(cb);
};

const onTokenRefreshed = (newToken: string) => {
  refreshSubscribers.forEach((cb) => cb(newToken));
  refreshSubscribers = [];
};

// Shared interceptor logic
function createAxiosInstance(baseURL: string): AxiosInstance {
  const instance = axios.create({ baseURL });

  // Request interceptor
  instance.interceptors.request.use((config) => {
    // const token = localStorage.getItem("access_token"); // or use context
    console.log("Getting auth token for request...");
    const token = getAuthToken();
    console.log("Auth token:", token);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log("Request config:", config);
    return config;
  });

  // Response interceptor
  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const originalRequest = error.config as any;

      if (error.response?.status === 401 && !originalRequest?._retry) {
        originalRequest._retry = true;

        if (isRefreshing) {
          // wait until token refreshed
          return new Promise((resolve) => {
            subscribeTokenRefresh((newToken) => {
              if (originalRequest?.headers)
                originalRequest.headers.Authorization = `Bearer ${newToken}`;
              resolve(instance(originalRequest!));
            });
          });
        }

        isRefreshing = true;

        try {
          const refreshToken = getRefreshToken();
          const response = await axios.post(
            `${baseURL}/auth/refresh?refresh_token=${refreshToken}`,
          );

          const newAccess = response.data.access_token;
          const newRefresh = response.data.refresh_token;

          localStorage.setItem("token", newAccess);
          localStorage.setItem("refreshToken", newRefresh);

          instance.defaults.headers.common["Authorization"] =
            `Bearer ${newAccess}`;
          onTokenRefreshed(newAccess);
          notifyTokenRefreshed(newAccess);
          isRefreshing = false;

          // retry original request
          if (originalRequest?.headers)
            originalRequest.headers.Authorization = `Bearer ${newAccess}`;
          return instance(originalRequest!);
        } catch (err) {
          isRefreshing = false;
          localStorage.clear();
          window.location.href = "/login";
          return Promise.reject(err);
        }
      }

      return Promise.reject(error);
    },
  );

  return instance;
}

// export const api = createAxiosInstance(baseURL);

export { createAxiosInstance };
