import { Activity, CheckCircle2, Images, ScanLine } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";
import { CountUp } from "@/features/batches/components/count-up";
import type { BatchOut } from "@/lib/api/types";

/**
 * Headline KPIs derived from the user's recent batches. `BatchOut` (the list
 * shape) carries status, image_count, and duration — enough for activity-level
 * stats without N detail fetches. Seed-level quality lives on the detail graph,
 * so it's intentionally not summarized here.
 */
interface DashboardStats {
  totalScans: number;
  totalImages: number;
  succeeded: number;
  successRate: number;
  /** Scans per day over the trailing window, oldest → newest, for a sparkline. */
  activity: number[];
}

function computeStats(batches: BatchOut[]): DashboardStats {
  const totalImages = batches.reduce((s, b) => s + (b.image_count ?? 0), 0);
  const succeeded = batches.filter(
    (b) => b.status === "succeeded" || b.status === "partial",
  ).length;

  // Bucket the trailing 14 days by submission date for the sparkline.
  const days = 14;
  const buckets = new Array<number>(days).fill(0);
  const now = Date.now();
  const dayMs = 86_400_000;
  for (const b of batches) {
    const t = new Date(b.submitted_at).getTime();
    if (Number.isNaN(t)) continue;
    const ago = Math.floor((now - t) / dayMs);
    const idx = days - 1 - ago;
    if (idx >= 0 && idx < days) buckets[idx] = (buckets[idx] ?? 0) + 1;
  }

  return {
    totalScans: batches.length,
    totalImages,
    succeeded,
    successRate: batches.length > 0 ? succeeded / batches.length : 0,
    activity: buckets,
  };
}

/** A tiny inline SVG sparkline (no chart lib). */
function Sparkline({ data }: { data: number[] }) {
  const max = Math.max(1, ...data);
  const w = 100;
  const h = 28;
  const step = data.length > 1 ? w / (data.length - 1) : w;
  const points = data
    .map((v, i) => `${(i * step).toFixed(1)},${(h - (v / max) * h).toFixed(1)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="h-7 w-full" preserveAspectRatio="none">
      <polyline
        points={points}
        fill="none"
        stroke="hsl(var(--primary))"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}

function StatCard({
  icon: Icon,
  label,
  value,
  decimals = 0,
  suffix = "",
  children,
}: {
  icon: typeof ScanLine;
  label: string;
  value?: number;
  decimals?: number;
  suffix?: string;
  children?: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <span className="text-xs uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
          <Icon className="h-4 w-4 text-primary" />
        </div>
        {value !== undefined ? (
          <div className="mt-1 text-2xl font-bold tabular-nums">
            <CountUp value={value} decimals={decimals} suffix={suffix} />
          </div>
        ) : null}
        {children}
      </CardContent>
    </Card>
  );
}

export function StatsStrip({ batches }: { batches: BatchOut[] }) {
  const stats = computeStats(batches);
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard icon={ScanLine} label="Total scans" value={stats.totalScans} />
      <StatCard icon={Images} label="Images analyzed" value={stats.totalImages} />
      <StatCard
        icon={CheckCircle2}
        label="Success rate"
        value={stats.successRate * 100}
        decimals={0}
        suffix="%"
      />
      <StatCard icon={Activity} label="Last 14 days">
        <div className="mt-2">
          <Sparkline data={stats.activity} />
        </div>
      </StatCard>
    </div>
  );
}

export { computeStats };
export type { DashboardStats };
