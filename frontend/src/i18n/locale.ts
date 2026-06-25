/**
 * Locale primitives shared by the i18n provider and the formatting helpers.
 *
 * A module-level "active locale" lets pure formatters (`format.ts`) localize
 * dates and numbers without threading the locale through every call site. The
 * provider is the single writer; everything else reads.
 */

export type Locale = "en" | "ar";

export const LOCALES: Locale[] = ["en", "ar"];

export const DEFAULT_LOCALE: Locale = "en";

/** Direction of each locale; drives `dir` on <html> and logical layout. */
export const LOCALE_DIR: Record<Locale, "ltr" | "rtl"> = {
  en: "ltr",
  ar: "rtl",
};

/** Native-script label for each locale (used in the language switcher). */
export const LOCALE_LABEL: Record<Locale, string> = {
  en: "English",
  ar: "العربية",
};

/**
 * BCP-47 tag handed to `Intl`. We pin Arabic to `ar-EG` (Egyptian) and force
 * Latin digits everywhere so numbers never mix scripts across the UI — Egyptian
 * users read Western numerals fluently and consistency reads calmer.
 */
export const LOCALE_INTL: Record<Locale, string> = {
  en: "en-US",
  ar: "ar-EG-u-nu-latn",
};

const STORAGE_KEY = "seedbank.locale";

let activeLocale: Locale = DEFAULT_LOCALE;

export function getLocale(): Locale {
  return activeLocale;
}

export function setActiveLocale(locale: Locale): void {
  activeLocale = locale;
}

export function isLocale(value: unknown): value is Locale {
  return value === "en" || value === "ar";
}

/** Persisted choice → browser language → default. Runs once on boot. */
export function resolveInitialLocale(): Locale {
  if (typeof window === "undefined") return DEFAULT_LOCALE;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (isLocale(stored)) return stored;
  } catch {
    // localStorage may be unavailable (private mode); fall through to detection.
  }
  const nav = window.navigator?.language?.toLowerCase() ?? "";
  if (nav.startsWith("ar")) return "ar";
  return DEFAULT_LOCALE;
}

export function persistLocale(locale: Locale): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, locale);
  } catch {
    // Best-effort; a failed persist just means the choice isn't remembered.
  }
}
