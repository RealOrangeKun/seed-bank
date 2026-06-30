import { api, unwrap } from "@/lib/api/client";
import { tokenStore } from "@/lib/auth/token-store";
import type { Envelope, MeOut, TokenPair } from "@/lib/api/types";
import { env as appEnv } from "@/lib/env";

/** Exchange credentials for a token pair and persist it. */
export async function login(email: string, password: string): Promise<void> {
  const result = await api.POST("/api/v1/auth/login", {
    body: { email, password },
  });
  const env = await unwrap<Envelope<TokenPair>>(result);
  tokenStore.setTokens(env.data.access_token, env.data.refresh_token);
}

/** Register a new end-user account. Backend sends a verification email. */
export async function register(input: {
  email: string;
  password: string;
  full_name: string | null;
}): Promise<string> {
  const result = await api.POST("/api/v1/auth/register", { body: input });
  const env = await unwrap<Envelope<{ message: string }>>(result);
  return env.data.message;
}

/** Confirm an email-verification token. */
export async function verifyEmail(token: string): Promise<string> {
  const result = await api.POST("/api/v1/auth/verify-email", { body: { token } });
  const env = await unwrap<Envelope<{ message: string }>>(result);
  return env.data.message;
}

/** OAuth providers the backend has configured — one sign-in button per entry. */
export async function fetchOAuthProviders(): Promise<string[]> {
  const result = await api.GET("/api/v1/auth/oauth/providers");
  const env = await unwrap<Envelope<string[]>>(result);
  return env.data;
}

/**
 * Full-page navigation target that starts the OAuth dance. The browser must
 * leave the SPA (the backend 302s to the provider), so this is a plain URL —
 * not a typed-client call.
 */
export function oauthLoginUrl(provider: string): string {
  return `${appEnv.apiOrigin}/api/v1/auth/oauth/${provider}/login`;
}

/** Current authenticated profile. Relies on the client's refresh-on-401. */
export async function fetchMe(): Promise<MeOut> {
  const result = await api.GET("/api/v1/users/me");
  const env = await unwrap<Envelope<MeOut>>(result);
  return env.data;
}

/** Revoke the stored refresh token server-side, then clear local tokens. */
export async function logout(): Promise<void> {
  const refresh = tokenStore.getRefreshToken();
  if (refresh) {
    try {
      await api.POST("/api/v1/auth/logout", { body: { refresh_token: refresh } });
    } catch {
      // Best-effort: even if the server call fails we still drop local tokens.
    }
  }
  tokenStore.clear();
}
