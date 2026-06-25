import { useCallback, useEffect, useMemo, useState } from "react";

import { ar, arPlurals } from "./dictionaries/ar";
import { en, enPlurals, type PluralKey, type TranslationKey } from "./dictionaries/en";
import {
  LOCALE_DIR,
  persistLocale,
  resolveInitialLocale,
  setActiveLocale,
  type Locale,
} from "./locale";
import { interpolate, selectPlural } from "./translate";
import { I18nContext, type I18nContextValue } from "./use-i18n";

const DICTS: Record<Locale, Record<TranslationKey, string>> = { en, ar };
const PLURALS = { en: enPlurals, ar: arPlurals } as const;

/**
 * Provides the translation context and keeps the document's `lang`/`dir` in
 * sync with the active locale (so the whole tree, including Radix portals and
 * native form controls, flips to RTL for Arabic). The provider is the single
 * writer of the module-level locale that `format.ts` reads.
 */
export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const initial = resolveInitialLocale();
    setActiveLocale(initial);
    return initial;
  });

  const dir = LOCALE_DIR[locale];

  useEffect(() => {
    setActiveLocale(locale);
    const root = document.documentElement;
    root.lang = locale;
    root.dir = dir;
  }, [locale, dir]);

  const setLocale = useCallback((next: Locale) => {
    persistLocale(next);
    setActiveLocale(next);
    setLocaleState(next);
  }, []);

  const t = useCallback<I18nContextValue["t"]>(
    (key, params) => interpolate(DICTS[locale][key] ?? en[key] ?? key, params),
    [locale],
  );

  const tn = useCallback<I18nContextValue["tn"]>(
    (key: PluralKey, count, params) => {
      const forms = PLURALS[locale][key] ?? enPlurals[key];
      return interpolate(selectPlural(forms, locale, count), { count, ...params });
    },
    [locale],
  );

  const value = useMemo<I18nContextValue>(
    () => ({ locale, dir, setLocale, t, tn }),
    [locale, dir, setLocale, t, tn],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}
