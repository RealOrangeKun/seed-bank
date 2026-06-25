import { getApiBaseUrl } from "./config";
import { tokenStore } from "./tokens";
import type { Envelope, TokenPair } from "./types";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

const AUTH_FRAGMENTS = ["/auth/login", "/auth/refresh", "/auth/register", "/auth/logout"];
const isAuthPath = (path: string) => AUTH_FRAGMENTS.some((p) => path.includes(p));

// Share one refresh round-trip across concurrent 401s.
let refreshInFlight: Promise<boolean> | null = null;

async function refreshTokens(): Promise<boolean> {
  const refresh = tokenStore.getRefresh();
  if (!refresh) return false;
  if (!refreshInFlight) {
    refreshInFlight = (async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!res.ok) return false;
        const env = (await res.json()) as Envelope<TokenPair>;
        await tokenStore.setTokens(env.data.access_token, env.data.refresh_token);
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

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  /** JSON body (ignored when `form` is set). */
  json?: unknown;
  /** Multipart body; Content-Type is left for the runtime to set the boundary. */
  form?: FormData;
}

async function rawFetch(path: string, opts: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};
  const token = tokenStore.getAccess();
  if (token && !isAuthPath(path)) headers.Authorization = `Bearer ${token}`;

  let body: BodyInit | undefined;
  if (opts.form) {
    body = opts.form as unknown as BodyInit;
  } else if (opts.json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(opts.json);
  }

  return fetch(`${getApiBaseUrl()}${path}`, {
    method: opts.method ?? "GET",
    headers,
    body,
  });
}

/** Fetch with bearer auth + a single transparent refresh-and-retry on 401. */
export async function apiFetch<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  let res: Response;
  try {
    res = await rawFetch(path, opts);
  } catch {
    throw new ApiError(0, "network");
  }

  if (res.status === 401 && !isAuthPath(path)) {
    const refreshed = await refreshTokens();
    if (refreshed) {
      res = await rawFetch(path, opts);
    } else {
      await tokenStore.clear();
    }
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const problem = (await res.json()) as { detail?: string; title?: string };
      message = problem.detail ?? problem.title ?? message;
    } catch {
      // Non-JSON error body; keep the status message.
    }
    throw new ApiError(res.status, message);
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

/** Unwrap a `{ data }` envelope. */
export async function apiData<T>(path: string, opts?: RequestOptions): Promise<T> {
  const env = await apiFetch<Envelope<T>>(path, opts);
  return env.data;
}
