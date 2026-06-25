/**
 * Pure translation primitives: placeholder interpolation and plural selection.
 * Kept dependency-free and side-effect-free so they're trivially unit-tested.
 */
import { LOCALE_INTL, type Locale } from "./locale";

/** A plural string set. `other` is always required as the fallback form. */
export type PluralForms = { other: string } & Partial<
  Record<Intl.LDMLPluralRule, string>
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

/** Pick the grammatically correct plural form for `count` in `locale`. */
export function selectPlural(
  forms: PluralForms,
  locale: Locale,
  count: number,
): string {
  const category = new Intl.PluralRules(LOCALE_INTL[locale]).select(count);
  return forms[category] ?? forms.other;
}
