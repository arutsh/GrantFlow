import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from "axios";
import { notifyTokenRefreshed } from "@/utils/tokenRefreshBridge";

type RetryableRequestConfig = InternalAxiosRequestConfig & { _retry?: boolean };

// sessionStorage first: it's per-tab, so a hit there is unambiguously this tab's session.
export const getAuthToken = (): string | null => {
  return sessionStorage.getItem("token") || localStorage.getItem("token");
};

// Also reports which store the token came from, so a refresh can write back to that store.
const getRefreshTokenSource = (): { token: string | null; store: Storage } => {
  const sessionToken = sessionStorage.getItem("refreshToken");
  if (sessionToken) return { token: sessionToken, store: sessionStorage };
  return { token: localStorage.getItem("refreshToken"), store: localStorage };
};

export const getRefreshToken = () => getRefreshTokenSource().token;

// Last API call made by the app, for the bug-report widget's context chip —
// not tied to any one gateway instance, since all of them share this module.
let lastApiCall: string | null = null;

function recordLastApiCall(method: string | undefined, url: string | undefined, status?: number) {
  if (!method || !url) return;
  lastApiCall = `${method.toUpperCase()} ${url} (${status ?? "network error"})`;
}

export function getLastApiCall(): string | null {
  return lastApiCall;
}

// Endpoints that can legitimately 401 on their own terms (bad credentials,
// no session yet) — a 401 from these must surface to the caller as-is, not
// trigger a silent-refresh attempt (there's nothing to refresh here) or the
// hard redirect that follows a failed refresh.
const AUTH_EXEMPT_PATHS = ["/auth/login", "/register", "/auth/refresh"];

function isAuthExempt(url?: string): boolean {
  return !!url && AUTH_EXEMPT_PATHS.some((path) => url.includes(path));
}

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
    const token = getAuthToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  });

  // Response interceptor
  instance.interceptors.response.use(
    (response) => {
      recordLastApiCall(response.config.method, response.config.url, response.status);
      return response;
    },
    async (error: AxiosError) => {
      const originalRequest = error.config as RetryableRequestConfig | undefined;
      recordLastApiCall(originalRequest?.method, originalRequest?.url, error.response?.status);

      if (
        error.response?.status === 403 &&
        (error.response.data as { detail?: string })?.detail === "email_not_verified" &&
        !isAuthExempt(originalRequest?.url)
      ) {
        // Valid token, just unverified — go confirm, don't try to refresh.
        // /auth/login itself is exempt: Login.tsx already routes this case
        // via a SPA navigate() that carries the typed email as router state,
        // which a hard redirect here would otherwise race and destroy.
        if (window.location.pathname !== "/confirm-email") {
          window.location.href = "/confirm-email";
        }
        return Promise.reject(error);
      }

      if (
        error.response?.status === 401 &&
        !originalRequest?._retry &&
        !isAuthExempt(originalRequest?.url)
      ) {
        const { token: refreshToken, store: refreshStore } = getRefreshTokenSource();
        if (!refreshToken) {
          // No session to refresh — let the 401 surface as-is instead of
          // firing a refresh call that can only fail (refresh_token=null)
          // and end in the hard-redirect below.
          return Promise.reject(error);
        }

        if (originalRequest) originalRequest._retry = true;

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
          const response = await axios.post(
            `${baseURL}/auth/refresh?refresh_token=${refreshToken}`,
          );

          const newAccess = response.data.access_token;
          const newRefresh = response.data.refresh_token;

          // Write back to the same store the refresh token came from.
          refreshStore.setItem("token", newAccess);
          refreshStore.setItem("refreshToken", newRefresh);

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
          sessionStorage.clear();
          // Avoid reload-looping if some other in-flight request also
          // 401s while we're already sitting on /login.
          if (window.location.pathname !== "/login") {
            window.location.href = "/login";
          }
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
