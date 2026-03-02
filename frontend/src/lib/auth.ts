import type { User } from "@/types";
import { authApi, clearTokens, storeTokens } from "./api";

export async function login(email: string, password: string): Promise<User> {
  const data = await authApi.login(email, password);
  storeTokens({ access: data.access, refresh: data.refresh });
  localStorage.setItem("retrievia_user", JSON.stringify(data.user));
  return data.user;
}

export function logout(): void {
  clearTokens();
}

export function getStoredUser(): User | null {
  if (typeof window === "undefined") return null;
  const raw = localStorage.getItem("retrievia_user");
  return raw ? JSON.parse(raw) : null;
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false;
  const raw = localStorage.getItem("retrievia_tokens");
  return Boolean(raw);
}
