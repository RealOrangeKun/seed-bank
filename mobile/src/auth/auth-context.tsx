import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import { fetchMe, login as apiLogin, logout as apiLogout } from "@/api/auth";
import { loadApiBaseUrl } from "@/api/config";
import { tokenStore } from "@/api/tokens";
import type { MeOut } from "@/api/types";

type Status = "loading" | "authenticated" | "unauthenticated";

interface AuthValue {
  status: Status;
  user: MeOut | null;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [user, setUser] = useState<MeOut | null>(null);

  // Hydrate config + tokens, then resolve the session against the server.
  useEffect(() => {
    let active = true;
    void (async () => {
      await loadApiBaseUrl();
      await tokenStore.load();
      if (!tokenStore.hasSession()) {
        if (active) setStatus("unauthenticated");
        return;
      }
      try {
        const me = await fetchMe();
        if (!active) return;
        setUser(me);
        setStatus("authenticated");
      } catch {
        await tokenStore.clear();
        if (active) setStatus("unauthenticated");
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    await apiLogin(email, password);
    const me = await fetchMe();
    setUser(me);
    setStatus("authenticated");
  }, []);

  const signOut = useCallback(async () => {
    await apiLogout();
    setUser(null);
    setStatus("unauthenticated");
  }, []);

  const value = useMemo<AuthValue>(
    () => ({ status, user, signIn, signOut }),
    [status, user, signIn, signOut],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
