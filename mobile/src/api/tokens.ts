import * as SecureStore from "expo-secure-store";

/**
 * Access/refresh tokens kept in the OS keystore (expo-secure-store) and mirrored
 * in memory so the request middleware can read them synchronously. Call `load()`
 * once at startup to hydrate from disk.
 */
const ACCESS_KEY = "seedbank.access";
const REFRESH_KEY = "seedbank.refresh";

let accessToken: string | null = null;
let refreshToken: string | null = null;

export const tokenStore = {
  async load(): Promise<void> {
    accessToken = await SecureStore.getItemAsync(ACCESS_KEY);
    refreshToken = await SecureStore.getItemAsync(REFRESH_KEY);
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
    await SecureStore.setItemAsync(ACCESS_KEY, access);
    await SecureStore.setItemAsync(REFRESH_KEY, refresh);
  },
  async clear(): Promise<void> {
    accessToken = null;
    refreshToken = null;
    await SecureStore.deleteItemAsync(ACCESS_KEY);
    await SecureStore.deleteItemAsync(REFRESH_KEY);
  },
};
