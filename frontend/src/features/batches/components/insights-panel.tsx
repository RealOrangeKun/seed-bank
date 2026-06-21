import { Sparkles } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

import type { BatchInsights } from "../insights";
import { CountUp } from "./count-up";

/** A donut showing the good / bad / unclassified split. */
function QualityDonut({ insights }: { insights: BatchInsights }) {
  const { good, bad, unclassified, total } = insights;
  const radius = 52;
  const circumference = 2 * Math.PI * radius;
  // Segment lengths proportional to each slice; falls back to a muted ring
  // when there are no detections so the widget never collapses to nothing.
  const segments =
    total > 0
      ? [
          { value: good, color: "hsl(var(--success))" },
          { value: bad, color: "hsl(var(--destructive))" },
          { value: unclassified, color: "hsl(var(--muted-foreground) / 0.4)" },
        ]
      : [{ value: 1, color: "hsl(var(--muted))" }];

  let offset = 0;
  const denom = total > 0 ? total : 1;

  return (
    <div className="relative h-36 w-36 shrink-0">
      <svg viewBox="0 0 128 128" className="h-full w-full -rotate-90">
        <circle
          cx="64"
          cy="64"
          r={radius}
          fill="none"
          stroke="hsl(var(--muted))"
          strokeWidth="14"
        />
        {segments.map((seg, i) => {
          const len = (seg.value / denom) * circumference;
          const dash = `${len} ${circumference - len}`;
          const el = (
            <circle
              key={i}
              cx="64"
              cy="64"
              r={radius}
              fill="none"
              stroke={seg.color}
              strokeWidth="14"
              strokeDasharray={dash}
              strokeDashoffset={-offset}
              strokeLinecap="butt"
              className="transition-[stroke-dashoffset,stroke-dasharray] duration-700 ease-out"
            />
          );
          offset += len;
          return el;
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-bold leading-none">
          <CountUp value={Math.round(insights.goodRate * 100)} suffix="%" />
        </span>
        <span className="text-[10px] uppercase tracking-wide text-muted-foreground">
          good rate
        </span>
      </div>
    </div>
  );
}

/** A compact 10-bucket confidence histogram. */
function ConfidenceHistogram({ insights }: { insights: BatchInsights }) {
  const max = Math.max(1, ...insights.confidenceBins.map((b) => b.count));
  return (
    <div className="flex-1">
      <div className="mb-1 flex items-end gap-1" style={{ height: 96 }}>
        {insights.confidenceBins.map((bin) => {
          const heightPct = (bin.count / max) * 100;
          // Tint ramps from amber (low confidence) to green (high) so the shape
          // and the color both read "how sure was the model".
          const hue = 30 + (bin.from + 0.05) * 110; // 30→140 across the range
          return (
            <div
              key={bin.from}
              className="group relative flex flex-1 items-end"
              style={{ height: "100%" }}
              title={`${Math.round(bin.from * 100)}–${Math.round(bin.to * 100)}%: ${bin.count}`}
            >
              <div
                className="w-full rounded-t-sm transition-all duration-500 ease-out"
                style={{
                  height: `${Math.max(bin.count > 0 ? 4 : 0, heightPct)}%`,
                  backgroundColor: `hsl(${hue} 55% 45%)`,
                }}
              />
            </div>
          );
        })}
      </div>
      <div className="flex justify-between text-[10px] text-muted-foreground">
        <span>0%</span>
        <span>confidence</span>
        <span>100%</span>
      </div>
    </div>
  );
}

function StatTile({
  label,
  value,
  decimals = 0,
  suffix = "",
  accent,
}: {
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
  accent?: "good" | "bad" | "muted";
}) {
  return (
    <div className="rounded-lg border bg-card p-3">
      <div
        className={cn(
          "text-xl font-semibold tabular-nums",
          accent === "good" && "text-[hsl(var(--success))]",
          accent === "bad" && "text-destructive",
        )}
      >
        <CountUp value={value} decimals={decimals} suffix={suffix} />
      </div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}

/**
 * The AI results header: a quality donut, a confidence histogram, and the
 * headline counts — all derived client-side from the batch's detection graph.
 * Shown above the per-image cards on the batch detail page.
 */
export function InsightsPanel({ insights }: { insights: BatchInsights }) {
  return (
    <Card className="overflow-hidden">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
          <Sparkles className="h-4 w-4 text-primary" />
          AI insights
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-6 lg:flex-row lg:items-center">
        <QualityDonut insights={insights} />
        <ConfidenceHistogram insights={insights} />
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 lg:w-80 lg:grid-cols-2">
          <StatTile label="Seeds detected" value={insights.total} />
          <StatTile
            label="Mean confidence"
            value={insights.meanConfidence * 100}
            decimals={1}
            suffix="%"
          />
          <StatTile label="Good" value={insights.good} accent="good" />
          <StatTile label="Bad" value={insights.bad} accent="bad" />
        </div>
      </CardContent>
    </Card>
  );
}
