import { Badge, type BadgeProps } from "@/components/ui/badge";
import { humanize } from "@/lib/format";

type Variant = NonNullable<BadgeProps["variant"]>;

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
  const variant = VARIANTS[status] ?? "secondary";
  return <Badge variant={variant}>{humanize(status)}</Badge>;
}
