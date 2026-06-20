/**
 * The single typed API client.
 *
 * Built on openapi-fetch + the generated `paths` type (run `npm run gen:api`),
 * so request/response shapes are checked against the backend's OpenAPI contract.
 * A custom middleware adds the bearer token and transparently refreshes it once
 * on a 401, retrying the original request. Auth endpoints opt out of that loop.
 *
 * Note: the generated `paths` keys include the `/api/v1` prefix, so the client
 * base URL is the API *origin* only.
 */
import createClient, { type Middleware } from "openapi-fetch";

import { tokenStore } from "@/lib/auth/token-store";
import { env } from "@/lib/env";

import { apiErrorFromResponse } from "./errors";
import type { paths } from "./schema";

/** Path fragments that must never trigger the refresh-retry loop. */
const AUTH_FRAGMENTS = ["/auth/login", "/auth/refresh", "/auth/register", "/auth/logout"];

function isAuthPath(url: string): boolean {
  return AUTH_FRAGMENTS.some((p) => url.includes(p));
}

export const api = createClient<paths>({ baseUrl: env.apiOrigin });

// Deduplicate concurrent refreshes: many in-flight requests hitting 401 at once
// should share one refresh round-trip, not stampede the endpoint.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.getRefreshToken();
  if (!refresh) return false;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        // Typed call; isAuthPath() keeps the middleware from recursing on it.
        const { data } = await api.POST("/api/v1/auth/refresh", {
          body: { refresh_token: refresh },
        });
        if (!data) return false;
        tokenStore.setTokens(data.data.access_token, data.data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshInFlight = null;
      }
    })();
  }
  return refreshInFlight;
}

const authMiddleware: Middleware = {
  onRequest({ request }) {
    const token = tokenStore.getAccessToken();
    if (token && !isAuthPath(request.url)) {
      request.headers.set("Authorization", `Bearer ${token}`);
    }
    return request;
  },
  async onResponse({ request, response }) {
    if (response.status !== 401 || isAuthPath(request.url)) return response;
    const refreshed = await refreshTokens();
    if (!refreshed) {
      tokenStore.clear();
      return response;
    }
    const retry = new Request(request.url, request);
    const token = tokenStore.getAccessToken();
    if (token) retry.headers.set("Authorization", `Bearer ${token}`);
    return fetch(retry);
  },
};

api.use(authMiddleware);

/**
 * Unwrap an openapi-fetch result: return `data` on success, throw `ApiError`
 * (with the parsed Problem) otherwise. Use in query/mutation functions so
 * components only ever see resolved data or a typed throw.
 */
export async function unwrap<T>(result: {
  data?: T;
  error?: unknown;
  response: Response;
}): Promise<T> {
  if (result.error !== undefined || !result.response.ok) {
    throw await apiErrorFromResponse(result.response);
  }
  return result.data as T;
}
