/**
 * Translation primitives. We implement CLDR plural categories by hand because
 * React Native's Hermes engine ships only a partial `Intl` (no reliable
 * `Intl.PluralRules` for Arabic). Pure + dependency-free, so it stays portable.
 */
import type { Locale } from "./locale";

export type PluralForms = { other: string } & Partial<
  Record<"zero" | "one" | "two" | "few" | "many" | "other", string>
>;

/** Replace `{name}` tokens with `params.name`; unknown tokens are left as-is. */
export function interpolate(
  template: string,
  params?: Record<string, string | number>,
): string {
  if (!params) return template;
  return template.replace(/\{(\w+)\}/g, (match, key: string) =>
    key in params ? String(params[key]) : match,
  );
}

type Category = "zero" | "one" | "two" | "few" | "many" | "other";

/** CLDR plural category for a count in the given locale. */
export function pluralCategory(locale: Locale, n: number): Category {
  if (locale === "ar") {
    if (n === 0) return "zero";
    if (n === 1) return "one";
    if (n === 2) return "two";
    const mod100 = n % 100;
    if (mod100 >= 3 && mod100 <= 10) return "few";
    if (mod100 >= 11 && mod100 <= 99) return "many";
    return "other";
  }
  return n === 1 ? "one" : "other";
}

export function selectPlural(
  forms: PluralForms,
  locale: Locale,
  count: number,
): string {
  return forms[pluralCategory(locale, count)] ?? forms.other;
}
