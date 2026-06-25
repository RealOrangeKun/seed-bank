import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";

/**
 * API origin (no `/api/v1` suffix — endpoints carry it). Defaults to the value
 * baked into app.json `extra.apiBaseUrl`, but can be overridden at runtime from
 * the Settings screen (handy when testing against a dev machine's LAN IP, since
 * `localhost` on a phone points at the phone itself).
 */
const OVERRIDE_KEY = "seedbank.apiBaseUrl";

const DEFAULT_BASE_URL =
  (Constants.expoConfig?.extra as { apiBaseUrl?: string } | undefined)?.apiBaseUrl ??
  "http://localhost:8000";

let baseUrl = DEFAULT_BASE_URL;

export function getApiBaseUrl(): string {
  return baseUrl.replace(/\/+$/, "");
}

/** Load any persisted override; call once during startup. */
export async function loadApiBaseUrl(): Promise<void> {
  const stored = await AsyncStorage.getItem(OVERRIDE_KEY);
  if (stored) baseUrl = stored;
}

export async function setApiBaseUrl(next: string): Promise<void> {
  baseUrl = next.trim() || DEFAULT_BASE_URL;
  await AsyncStorage.setItem(OVERRIDE_KEY, baseUrl);
}
