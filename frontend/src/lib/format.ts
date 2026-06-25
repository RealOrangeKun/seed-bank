/**
 * Display formatting helpers.
 *
 * The API emits `confidence` and bounding-box coordinates as decimal *strings*
 * (NUMERIC columns) to avoid float drift. We keep them as strings end-to-end
 * and only parse to a number at the moment of rendering.
 */
import { getLocale, LOCALE_INTL } from "@/i18n/locale";

/** BCP-47 tag for the active locale (Latin digits, localized month names). */
function intlLocale(): string {
  return LOCALE_INTL[getLocale()];
}

/** Parse an API decimal string (or number) to a JS number for layout/rendering. */
export function toNumber(value: string | number | null | undefined): number {
  if (value === null || value === undefined) return 0;
  return typeof value === "number" ? value : Number.parseFloat(value);
}

/** Format a 0–1 confidence as a percentage, e.g. "92.3%". */
export function formatConfidence(value: string | number | null | undefined): string {
  return `${(toNumber(value) * 100).toFixed(1)}%`;
}

/** Locale date-time, e.g. "Jun 20, 2026, 14:05". Empty string for nullish. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleString(intlLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/** Relative-ish short date, e.g. "Jun 20, 2026". */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString(intlLocale(), {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

/** Human-readable duration from milliseconds, e.g. "1.2s" or "340ms". */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

/** Human-readable byte size, e.g. "1.4 MB". */
export function formatBytes(bytes: number | null | undefined): string {
  if (!bytes) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let n = bytes;
  let u = 0;
  while (n >= 1024 && u < units.length - 1) {
    n /= 1024;
    u += 1;
  }
  return `${n.toFixed(u === 0 ? 0 : 1)} ${units[u]}`;
}

/** Short UUID for display, e.g. "a1b2c3d4". */
export function shortId(id: string | null | undefined): string {
  return id ? id.slice(0, 8) : "—";
}

/** Title-case a snake_case enum value, e.g. "ai_developer" → "Ai Developer". */
export function humanize(value: string | null | undefined): string {
  if (!value) return "—";
  return value
    .split(/[_\s]+/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
