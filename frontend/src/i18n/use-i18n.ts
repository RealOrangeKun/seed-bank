import { createContext, useContext } from "react";

import type { Locale } from "./locale";
import type { PluralKey, TranslationKey } from "./dictionaries/en";

export interface I18nContextValue {
  locale: Locale;
  /** Text direction for the active locale; mirror onto layout when needed. */
  dir: "ltr" | "rtl";
  setLocale: (locale: Locale) => void;
  /** Translate a key, filling `{name}` tokens from `params`. */
  t: (key: TranslationKey, params?: Record<string, string | number>) => string;
  /** Translate a count-sensitive phrase; `count` also fills `{count}`. */
  tn: (
    key: PluralKey,
    count: number,
    params?: Record<string, string | number>,
  ) => string;
}

export const I18nContext = createContext<I18nContextValue | null>(null);

export function useI18n(): I18nContextValue {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within <I18nProvider>");
  return ctx;
}
