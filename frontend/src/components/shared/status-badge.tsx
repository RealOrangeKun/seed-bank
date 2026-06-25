import { Badge, type BadgeProps } from "@/components/ui/badge";
import type { TranslationKey } from "@/i18n/dictionaries/en";
import { useI18n } from "@/i18n";
import { humanize } from "@/lib/format";

type Variant = NonNullable<BadgeProps["variant"]>;

// Status enums we have a localized label for. Anything else (rare/technical,
// e.g. backend names) falls back to a humanized English string.
const LABELS: Record<string, TranslationKey> = {
  succeeded: "status.succeeded",
  running: "status.running",
  pending: "status.pending",
  failed: "status.failed",
  partial: "status.partial",
  production: "status.production",
  staging: "status.staging",
  registered: "status.registered",
  archived: "status.archived",
  good: "status.good",
  bad: "status.bad",
  active: "status.active",
  // roles (shown as a badge in the topbar and profile)
  end_user: "role.end_user",
  ai_developer: "role.ai_developer",
  admin: "role.admin",
};

// Maps the various backend status enums onto badge variants. Terminal-good →
// success, terminal-bad → destructive, in-flight → warning, neutral → secondary.
const VARIANTS: Record<string, Variant> = {
  // batch / experiment
  succeeded: "success",
  running: "warning",
  pending: "secondary",
  failed: "destructive",
  partial: "warning",
  // model lifecycle
  production: "success",
  staging: "warning",
  registered: "secondary",
  archived: "outline",
  // seed quality
  good: "success",
  bad: "destructive",
  // user flags
  active: "success",
};

export function StatusBadge({ status }: { status: string }) {
  const { t } = useI18n();
  const variant = VARIANTS[status] ?? "secondary";
  const labelKey = LABELS[status];
  return <Badge variant={variant}>{labelKey ? t(labelKey) : humanize(status)}</Badge>;
}
