// axiosConfig.ts's silent 401-refresh interceptor writes a newly-issued token
// straight to storage without going through AuthContext's React state — so
// nav/role-flag decisions (isNgo/isDonor) would otherwise stay pinned to the
// pre-refresh token until a full reload. This lets that interceptor notify
// AuthContext directly instead.
type TokenRefreshListener = (token: string) => void;
let listeners: TokenRefreshListener[] = [];

export function onTokenRefreshed(listener: TokenRefreshListener): () => void {
  listeners.push(listener);
  return () => {
    listeners = listeners.filter((l) => l !== listener);
  };
}

export function notifyTokenRefreshed(token: string) {
  listeners.forEach((listener) => listener(token));
}
