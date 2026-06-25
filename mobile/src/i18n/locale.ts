export type Locale = "en" | "ar";

export const LOCALES: Locale[] = ["en", "ar"];

export const LOCALE_LABEL: Record<Locale, string> = {
  en: "English",
  ar: "العربية",
};

export const STORAGE_KEY = "seedbank.locale";

export function isLocale(value: unknown): value is Locale {
  return value === "en" || value === "ar";
}

export function isRtl(locale: Locale): boolean {
  return locale === "ar";
}

/**
 * Compact, Hermes-safe date formatter: `DD/MM/YYYY HH:mm` with Latin digits.
 * Avoids `Intl`/`toLocaleString`, which is unreliable on React Native, while
 * staying readable for both English and Arabic users.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const p = (n: number) => String(n).padStart(2, "0");
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} ${p(
    d.getHours(),
  )}:${p(d.getMinutes())}`;
}
