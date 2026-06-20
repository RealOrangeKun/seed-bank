import { Badge } from "@/components/ui/badge";
import { formatConfidence, toNumber } from "@/lib/format";

/** Confidence shown as a percentage, color-graded by strength. */
export function ConfidenceBadge({ value }: { value: string | number | null | undefined }) {
  const n = toNumber(value);
  const variant = n >= 0.75 ? "success" : n >= 0.5 ? "warning" : "destructive";
  return <Badge variant={variant}>{formatConfidence(value)}</Badge>;
}
