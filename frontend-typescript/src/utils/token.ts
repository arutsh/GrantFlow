import {jwtDecode} from "jwt-decode";

export interface JwtPayload {
  user_id: string; // standard field for user ID
  exp?: number;
  iat?: number;
  [key: string]: any; // allow extra fields
}

export function safeDecodeToken<T>(token: string | null): T | null {
  if (!token) return null;

  try {
    return jwtDecode<T>(token);
  } catch (error) {
    console.error("Invalid token:", error);
    return null;
  }
}

export function getUserIdFromToken(token: string | null): string | null {
  return safeDecodeToken<JwtPayload>(token)?.user_id ?? null;
}
