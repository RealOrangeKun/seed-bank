import { useCallback, useEffect, useMemo, useState } from "react";

import { ensureAccessToken } from "@/lib/api/client";
import { tokenStore } from "@/lib/auth/token-store";
import type { MeOut } from "@/lib/api/types";

import * as authApi from "./api";
import { AuthContext, type AuthStatus } from "./use-auth";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<MeOut | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  const loadMe = useCallback(async () => {
    const me = await authApi.fetchMe();
    setUser(me);
    setStatus("authenticated");
  }, []);

  // On mount, recover a session if a refresh token is present. Proactively mint
  // an access token from it *before* the first authed call, so a normal reload
  // doesn't fire a guaranteed-401 `/users/me` (which shows up as a misleading
  // "Unauthorized" error). A rejected/stale refresh token resolves to false →
  // we clear it and fall back to the login screen.
  useEffect(() => {
    let active = true;
    if (!tokenStore.hasSession()) {
      setStatus("unauthenticated");
      return;
    }
    ensureAccessToken()
      .then((ok) => {
        if (!ok) throw new Error("session expired");
        return authApi.fetchMe();
      })
      .then((me) => {
        if (!active) return;
        setUser(me);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!active) return;
        tokenStore.clear();
        setUser(null);
        setStatus("unauthenticated");
      });
    return () => {
      active = false;
    };
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      await authApi.login(email, password);
      await loadMe();
    },
    [loadMe],
  );

  const loginWithTokens = useCallback(
    async (accessToken: string, refreshToken: string) => {
      tokenStore.setTokens(accessToken, refreshToken);
      await loadMe();
    },
    [loadMe],
  );

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const refreshMe = useCallback(async () => {
    await loadMe();
  }, [loadMe]);

  const value = useMemo(
    () => ({ user, status, login, loginWithTokens, logout, refreshMe }),
    [user, status, login, loginWithTokens, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
