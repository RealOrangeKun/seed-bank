import { Platform } from "react-native";

/**
 * Access/refresh tokens kept in the OS keystore (expo-secure-store) and mirrored
 * in memory so the request middleware can read them synchronously. Call `load()`
 * once at startup to hydrate from disk.
 *
 * On web, falls back to localStorage (expo-secure-store has no web support).
 */
const ACCESS_KEY = "seedbank.access";
const REFRESH_KEY = "seedbank.refresh";

let accessToken: string | null = null;
let refreshToken: string | null = null;

// ── Tiny storage shim ─────────────────────────────────────────────────────
const storage = {
  async getItem(key: string): Promise<string | null> {
    if (Platform.OS === "web") return localStorage.getItem(key);
    const SecureStore = await import("expo-secure-store");
    return SecureStore.getItemAsync(key);
  },
  async setItem(key: string, value: string): Promise<void> {
    if (Platform.OS === "web") { localStorage.setItem(key, value); return; }
    const SecureStore = await import("expo-secure-store");
    await SecureStore.setItemAsync(key, value);
  },
  async removeItem(key: string): Promise<void> {
    if (Platform.OS === "web") { localStorage.removeItem(key); return; }
    const SecureStore = await import("expo-secure-store");
    await SecureStore.deleteItemAsync(key);
  },
};

export const tokenStore = {
  async load(): Promise<void> {
    accessToken = await storage.getItem(ACCESS_KEY);
    refreshToken = await storage.getItem(REFRESH_KEY);
  },
  getAccess(): string | null {
    return accessToken;
  },
  getRefresh(): string | null {
    return refreshToken;
  },
  hasSession(): boolean {
    return Boolean(accessToken || refreshToken);
  },
  async setTokens(access: string, refresh: string): Promise<void> {
    accessToken = access;
    refreshToken = refresh;
    await storage.setItem(ACCESS_KEY, access);
    await storage.setItem(REFRESH_KEY, refresh);
  },
  async clear(): Promise<void> {
    accessToken = null;
    refreshToken = null;
    await storage.removeItem(ACCESS_KEY);
    await storage.removeItem(REFRESH_KEY);
  },
};
