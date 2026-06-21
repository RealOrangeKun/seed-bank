import { useCallback, useEffect, useMemo, useState } from "react";

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

  // On mount, recover a session if a refresh token is present. The API client
  // mints a fresh access token from it via refresh-on-401.
  useEffect(() => {
    let active = true;
    if (!tokenStore.hasSession()) {
      setStatus("unauthenticated");
      return;
    }
    authApi
      .fetchMe()
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

  const logout = useCallback(async () => {
    await authApi.logout();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const refreshMe = useCallback(async () => {
    await loadMe();
  }, [loadMe]);

  const value = useMemo(
    () => ({ user, status, login, logout, refreshMe }),
    [user, status, login, logout, refreshMe],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
