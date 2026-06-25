import { apiData, apiFetch } from "./client";
import { tokenStore } from "./tokens";
import type { Envelope, MeOut, TokenPair } from "./types";

/** Exchange credentials for tokens and persist them in the keystore. */
export async function login(email: string, password: string): Promise<void> {
  const env = await apiFetch<Envelope<TokenPair>>("/api/v1/auth/login", {
    method: "POST",
    json: { email, password },
  });
  await tokenStore.setTokens(env.data.access_token, env.data.refresh_token);
}

export async function fetchMe(): Promise<MeOut> {
  return apiData<MeOut>("/api/v1/users/me");
}

/** Revoke the refresh token server-side (best-effort), then clear locally. */
export async function logout(): Promise<void> {
  const refresh = tokenStore.getRefresh();
  if (refresh) {
    try {
      await apiFetch("/api/v1/auth/logout", {
        method: "POST",
        json: { refresh_token: refresh },
      });
    } catch {
      // Even if the server call fails, drop local tokens below.
    }
  }
  await tokenStore.clear();
}
