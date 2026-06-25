import AsyncStorage from "@react-native-async-storage/async-storage";
import * as Updates from "expo-updates";
import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { I18nManager } from "react-native";

import { ar, arPlurals } from "./dictionaries/ar";
import { en, enPlurals, type PluralKey, type TranslationKey } from "./dictionaries/en";
import { isLocale, isRtl, STORAGE_KEY, type Locale } from "./locale";
import { interpolate, selectPlural } from "./translate";

const DICTS: Record<Locale, Record<TranslationKey, string>> = { en, ar };
const PLURALS = { en: enPlurals, ar: arPlurals } as const;

interface I18nValue {
  locale: Locale;
  isRTL: boolean;
  setLocale: (locale: Locale) => Promise<void>;
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
  tn: (
    key: PluralKey,
    count: number,
    params?: Record<string, string | number>,
  ) => string;
}

const I18nContext = createContext<I18nValue | null>(null);

/** Reload the app so a layout-direction change takes effect (RN requirement). */
async function reloadApp(): Promise<void> {
  try {
    await Updates.reloadAsync();
  } catch {
    // Expo Go / dev: reload may be unavailable. Layout flips on next launch.
  }
}

/** Force native RTL only when it actually changes, then reload to apply it. */
function applyDirection(locale: Locale): void {
  const shouldRtl = isRtl(locale);
  if (I18nManager.isRTL !== shouldRtl) {
    I18nManager.allowRTL(shouldRtl);
    I18nManager.forceRTL(shouldRtl);
    void reloadApp();
  }
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  // Seed from the native RTL flag so text and layout agree at cold start.
  const [locale, setLocaleState] = useState<Locale>(
    I18nManager.isRTL ? "ar" : "en",
  );

  useEffect(() => {
    let active = true;
    void AsyncStorage.getItem(STORAGE_KEY).then((stored) => {
      if (active && isLocale(stored)) {
        setLocaleState(stored);
        applyDirection(stored);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const value = useMemo<I18nValue>(() => {
    const setLocale = async (next: Locale) => {
      await AsyncStorage.setItem(STORAGE_KEY, next);
      setLocaleState(next);
      applyDirection(next);
    };
    return {
      locale,
      isRTL: isRtl(locale),
      setLocale,
      t: (key, params) => interpolate(DICTS[locale][key] ?? en[key] ?? key, params),
      tn: (key, count, params) =>
        interpolate(selectPlural(PLURALS[locale][key] ?? enPlurals[key], locale, count), {
          count,
          ...params,
        }),
    };
  }, [locale]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within <I18nProvider>");
  return ctx;
}
