import AsyncStorage from "@react-native-async-storage/async-storage";
import * as SecureStore from "expo-secure-store";
import { Platform } from "react-native";

/**
 * Access/refresh tokens kept in the OS keystore (expo-secure-store) and mirrored
 * in memory so the request middleware can read them synchronously. Call `load()`
 * once at startup to hydrate from disk.
 *
 * `expo-secure-store` has no web implementation (its methods throw in the
 * browser), so under Expo web we fall back to AsyncStorage — which is
 * localStorage-backed there. This keeps the app usable on web for manual
 * testing; native builds still use the secure keystore.
 */
const ACCESS_KEY = "seedbank.access";
const REFRESH_KEY = "seedbank.refresh";

const isWeb = Platform.OS === "web";

async function readItem(key: string): Promise<string | null> {
  return isWeb ? AsyncStorage.getItem(key) : SecureStore.getItemAsync(key);
}

async function writeItem(key: string, value: string): Promise<void> {
  if (isWeb) {
    await AsyncStorage.setItem(key, value);
  } else {
    await SecureStore.setItemAsync(key, value);
  }
}

async function removeItem(key: string): Promise<void> {
  if (isWeb) {
    await AsyncStorage.removeItem(key);
  } else {
    await SecureStore.deleteItemAsync(key);
  }
}

let accessToken: string | null = null;
let refreshToken: string | null = null;

export const tokenStore = {
  async load(): Promise<void> {
    accessToken = await readItem(ACCESS_KEY);
    refreshToken = await readItem(REFRESH_KEY);
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
    await writeItem(ACCESS_KEY, access);
    await writeItem(REFRESH_KEY, refresh);
  },
  async clear(): Promise<void> {
    accessToken = null;
    refreshToken = null;
    await removeItem(ACCESS_KEY);
    await removeItem(REFRESH_KEY);
  },
};
