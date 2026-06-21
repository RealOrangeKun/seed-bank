/**
 * Token storage.
 *
 * Access token lives in memory only (cleared on reload — re-minted from the
 * refresh token at startup), which keeps it off disk where XSS-readable
 * storage is riskier. The refresh token is persisted in localStorage so a
 * reload can recover the session. This is the pragmatic SPA trade-off given
 * the API returns tokens in the response body rather than httpOnly cookies.
 */
const REFRESH_KEY = "seedbank.refresh_token";

let accessToken: string | null = null;
type Listener = () => void;
const listeners = new Set<Listener>();

function notify(): void {
  for (const l of listeners) l();
}

export const tokenStore = {
  getAccessToken(): string | null {
    return accessToken;
  },
  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  /** Persist a freshly issued access+refresh pair. */
  setTokens(access: string, refresh: string): void {
    accessToken = access;
    localStorage.setItem(REFRESH_KEY, refresh);
    notify();
  },
  clear(): void {
    accessToken = null;
    localStorage.removeItem(REFRESH_KEY);
    notify();
  },
  /** True when a refresh token exists — i.e. a session is recoverable. */
  hasSession(): boolean {
    return Boolean(localStorage.getItem(REFRESH_KEY));
  },
  subscribe(listener: Listener): () => void {
    listeners.add(listener);
    return () => listeners.delete(listener);
  },
};
