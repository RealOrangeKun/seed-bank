import { Tag } from "lucide-react";

import type { TranslationKey } from "@/i18n/dictionaries/en";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/utils";

export type QualityKey = "good" | "bad" | "unclassified";

const QUALITY_META: Record<QualityKey, { labelKey: TranslationKey; color: string }> = {
  good: { labelKey: "overlay.good", color: "hsl(var(--success))" },
  bad: { labelKey: "overlay.bad", color: "hsl(var(--destructive))" },
  unclassified: { labelKey: "overlay.unclassified", color: "hsl(var(--primary))" },
};

interface OverlayControlsProps {
  active: Set<QualityKey>;
  onToggleQuality: (key: QualityKey) => void;
  minConfidence: number;
  onMinConfidenceChange: (value: number) => void;
  showLabels: boolean;
  onToggleLabels: () => void;
  /** Count of detections currently passing the filters (for the live count). */
  visibleCount: number;
  totalCount: number;
}

/**
 * Interactive controls for the bounding-box overlay: per-quality legend chips
 * that double as filter toggles, a confidence threshold slider, and a label
 * toggle. Lets a reviewer focus on, say, just the low-confidence "bad" calls.
 */
export function OverlayControls({
  active,
  onToggleQuality,
  minConfidence,
  onMinConfidenceChange,
  showLabels,
  onToggleLabels,
  visibleCount,
  totalCount,
}: OverlayControlsProps) {
  const { t } = useI18n();
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs">
      <div className="flex items-center gap-1.5">
        {(Object.keys(QUALITY_META) as QualityKey[]).map((key) => {
          const on = active.has(key);
          const meta = QUALITY_META[key];
          return (
            <button
              key={key}
              type="button"
              onClick={() => onToggleQuality(key)}
              aria-pressed={on}
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 transition-colors",
                on ? "bg-accent" : "opacity-50 hover:opacity-80",
              )}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: meta.color }}
              />
              {t(meta.labelKey)}
            </button>
          );
        })}
      </div>

      <label className="flex items-center gap-2">
        <span className="text-muted-foreground">
          {t("overlay.minConfidence")}{" "}
          <span className="font-medium text-foreground">
            {Math.round(minConfidence * 100)}%
          </span>
        </span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={Math.round(minConfidence * 100)}
          onChange={(e) => onMinConfidenceChange(Number(e.target.value) / 100)}
          className="h-1 w-28 cursor-pointer accent-[hsl(var(--primary))]"
          aria-label={t("overlay.minConfidence")}
        />
      </label>

      <button
        type="button"
        onClick={onToggleLabels}
        aria-pressed={showLabels}
        className={cn(
          "inline-flex items-center gap-1 rounded-full border px-2 py-0.5 transition-colors",
          showLabels ? "bg-accent" : "opacity-60 hover:opacity-90",
        )}
      >
        <Tag className="h-3 w-3" /> {t("overlay.labels")}
      </button>

      <span className="ms-auto text-muted-foreground">
        {t("overlay.showing", { visible: visibleCount, total: totalCount })}
      </span>
    </div>
  );
}
