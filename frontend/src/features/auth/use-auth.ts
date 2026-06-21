import { createContext, useContext } from "react";

import type { MeOut, Role } from "@/lib/api/types";

export type AuthStatus = "loading" | "authenticated" | "unauthenticated";

export interface AuthContextValue {
  user: MeOut | null;
  status: AuthStatus;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

/**
 * Role check used by route guards and conditional UI. `admin` satisfies every
 * requirement (mirrors the backend's `require_role`, where admin ⊇ all).
 */
export function hasRole(user: MeOut | null, allowed: Role[]): boolean {
  if (!user) return false;
  if (user.role === "admin") return true;
  return allowed.includes(user.role);
}
