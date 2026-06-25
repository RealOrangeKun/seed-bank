import { useMemo, useState } from "react";

import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useI18n } from "@/i18n";
import { formatConfidence, humanize, toNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { SeedDetectionOut } from "@/lib/api/types";

interface BBoxOverlayProps {
  src: string;
  detections: SeedDetectionOut[];
  /** Optional map of seed_type_id → display label. */
  seedTypeLabels?: Record<string, string>;
  alt?: string;
  /** Hide detections whose confidence is below this 0–1 threshold. */
  minConfidence?: number;
  /** Only draw detections whose quality is in this set (undefined = all). */
  qualityFilter?: Set<string | "unclassified">;
  /** Show a small confidence label inside each box. */
  showLabels?: boolean;
}

function boxColor(d: SeedDetectionOut): string {
  if (d.quality === "good") return "hsl(var(--success))";
  if (d.quality === "bad") return "hsl(var(--destructive))";
  return "hsl(var(--primary))";
}

/**
 * Renders an image with detection boxes overlaid. Boxes are stored normalized
 * (0–1), so we position them with CSS percentages — resolution-independent,
 * scales with the rendered image.
 */
export function BBoxOverlay({
  src,
  detections,
  seedTypeLabels,
  alt,
  minConfidence = 0,
  qualityFilter,
  showLabels = false,
}: BBoxOverlayProps) {
  const [hovered, setHovered] = useState<number | null>(null);
  const { t } = useI18n();
  const qualityLabel = (q: string | null | undefined) =>
    q === "good" ? t("overlay.good") : q === "bad" ? t("overlay.bad") : humanize(q);

  // Apply confidence + quality filters. Keep the original index so hover state
  // and aria labels stay stable as filters change.
  const visible = useMemo(
    () =>
      detections
        .map((d, i) => ({ d, i }))
        .filter(({ d }) => toNumber(d.confidence) >= minConfidence)
        .filter(({ d }) => {
          if (!qualityFilter) return true;
          const key = d.quality ?? "unclassified";
          return qualityFilter.has(key);
        }),
    [detections, minConfidence, qualityFilter],
  );

  return (
    <TooltipProvider delayDuration={100}>
      <div className="relative inline-block max-w-full overflow-hidden rounded-lg border bg-muted">
        <img src={src} alt={alt ?? t("bbox.scanImage")} className="block max-w-full" />
        {visible.map(({ d, i }) => {
          const left = toNumber(d.box_x_norm) * 100;
          const top = toNumber(d.box_y_norm) * 100;
          const width = toNumber(d.box_w_norm) * 100;
          const height = toNumber(d.box_h_norm) * 100;
          const label = d.seed_type_id ? seedTypeLabels?.[d.seed_type_id] : undefined;
          return (
            <Tooltip key={d.id} open={hovered === i}>
              <TooltipTrigger asChild>
                <div
                  role="button"
                  tabIndex={0}
                  aria-label={t("bbox.detection", { n: i + 1 })}
                  onMouseEnter={() => setHovered(i)}
                  onMouseLeave={() => setHovered((h) => (h === i ? null : h))}
                  onFocus={() => setHovered(i)}
                  onBlur={() => setHovered((h) => (h === i ? null : h))}
                  className={cn(
                    "absolute cursor-pointer rounded-sm border-2 transition-all",
                    hovered === i ? "z-10 shadow-lg" : "opacity-80",
                  )}
                  style={{
                    left: `${left}%`,
                    top: `${top}%`,
                    width: `${width}%`,
                    height: `${height}%`,
                    borderColor: boxColor(d),
                    backgroundColor: hovered === i ? `${boxColor(d)}22` : "transparent",
                  }}
                >
                  {showLabels ? (
                    <span
                      className="absolute -top-4 left-0 rounded px-1 text-[9px] font-medium leading-tight text-white"
                      style={{ backgroundColor: boxColor(d) }}
                    >
                      {formatConfidence(d.confidence)}
                    </span>
                  ) : null}
                </div>
              </TooltipTrigger>
              <TooltipContent className="space-y-0.5">
                <div className="font-medium">
                  {label ?? (d.quality ? qualityLabel(d.quality) : t("bbox.detectionTitle"))}
                </div>
                <div>
                  {t("bbox.confidence")}: {formatConfidence(d.confidence)}
                </div>
                {d.quality ? (
                  <div>
                    {t("bbox.quality")}: {qualityLabel(d.quality)}
                  </div>
                ) : null}
              </TooltipContent>
            </Tooltip>
          );
        })}
      </div>
    </TooltipProvider>
  );
}
