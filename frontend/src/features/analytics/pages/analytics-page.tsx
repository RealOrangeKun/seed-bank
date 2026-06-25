import { Activity, CheckCircle2, Images, Sprout } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CountUp } from "@/features/batches/components/count-up";
import { useSeedTypes } from "@/features/catalog/api";
import { useI18n } from "@/i18n";
import { cn } from "@/lib/utils";

import { useAnalytics, type AnalyticsOut } from "../api";

const WINDOWS = [7, 30, 90] as const;

function StatCard({
  icon: Icon,
  label,
  value,
  decimals = 0,
  suffix = "",
}: {
  icon: typeof Activity;
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
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
        <div className="mt-1 text-2xl font-bold tabular-nums">
          <CountUp value={value} decimals={decimals} suffix={suffix} />
        </div>
      </CardContent>
    </Card>
  );
}

/** Per-day batches bar chart across the window. */
function TrendChart({ trend }: { trend: AnalyticsOut["trend"] }) {
  const { t, tn } = useI18n();
  const max = Math.max(1, ...trend.map((d) => d.batches));
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("analytics.activity")}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-0.5" style={{ height: 120 }}>
          {trend.map((d) => (
            <div
              key={d.day}
              className="group relative flex flex-1 items-end"
              style={{ height: "100%" }}
              title={`${d.day}: ${tn("scans", d.batches)} · ${tn("seeds", d.detections)}`}
            >
              <div
                className="w-full rounded-t-sm bg-primary/70 transition-all duration-500 ease-out group-hover:bg-primary"
                style={{
                  height: `${d.batches > 0 ? Math.max(4, (d.batches / max) * 100) : 0}%`,
                }}
              />
            </div>
          ))}
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
          <span>{trend[0]?.day}</span>
          <span>{t("analytics.scansPerDay")}</span>
          <span>{trend[trend.length - 1]?.day}</span>
        </div>
      </CardContent>
    </Card>
  );
}

/** 10-bucket confidence histogram, amber→green. */
function ConfidenceChart({ bins }: { bins: AnalyticsOut["confidence_histogram"] }) {
  const { t } = useI18n();
  const max = Math.max(1, ...bins.map((b) => b.count));
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">
          {t("analytics.confidenceDistribution")}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex items-end gap-1" style={{ height: 120 }}>
          {bins.map((b) => {
            const hue = 30 + (b.from_pct / 100 + 0.05) * 110;
            return (
              <div
                key={b.from_pct}
                className="flex flex-1 items-end"
                style={{ height: "100%" }}
                title={`${b.from_pct}–${b.to_pct}%: ${b.count}`}
              >
                <div
                  className="w-full rounded-t-sm transition-all duration-500 ease-out"
                  style={{
                    height: `${b.count > 0 ? Math.max(4, (b.count / max) * 100) : 0}%`,
                    backgroundColor: `hsl(${hue} 55% 45%)`,
                  }}
                />
              </div>
            );
          })}
        </div>
        <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
          <span>0%</span>
          <span>{t("analytics.detectionConfidence")}</span>
          <span>100%</span>
        </div>
      </CardContent>
    </Card>
  );
}

/** Per-seed-type good/bad split bars. */
function TypeSplit({
  rows,
  seedTypeName,
}: {
  rows: AnalyticsOut["type_split"];
  seedTypeName: (id: string | null | undefined) => string;
}) {
  const { t } = useI18n();
  if (rows.length === 0) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">{t("analytics.qualityBySeedType")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="py-4 text-center text-sm text-muted-foreground">
            {t("analytics.noDetections")}
          </p>
        </CardContent>
      </Card>
    );
  }
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("analytics.qualityBySeedType")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map((row) => {
          const total = row.total || 1;
          return (
            <div key={row.seed_type_id ?? "unclassified"} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">
                  {row.seed_type_id
                    ? seedTypeName(row.seed_type_id)
                    : t("analytics.unclassified")}
                </span>
                <span className="text-xs text-muted-foreground">
                  {row.total}
                  {t("breakdown.goodSuffix", { rate: Math.round(row.good_rate * 100) })}
                </span>
              </div>
              <div className="flex h-2.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="bg-[hsl(var(--success))] transition-[width] duration-700"
                  style={{ width: `${(row.good / total) * 100}%` }}
                />
                <div
                  className="bg-destructive transition-[width] duration-700"
                  style={{ width: `${(row.bad / total) * 100}%` }}
                />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

export function AnalyticsPage() {
  const { t } = useI18n();
  const [windowDays, setWindowDays] = useState<number>(30);
  const query = useAnalytics(windowDays);
  const seedTypes = useSeedTypes();
  const seedTypeMap = new Map((seedTypes.data ?? []).map((s) => [s.id, s.display_name]));
  const seedTypeName = (id: string | null | undefined) =>
    id ? (seedTypeMap.get(id) ?? t("analytics.unknown")) : t("analytics.unclassified");

  return (
    <>
      <PageHeader
        title={t("analytics.title")}
        description={t("analytics.description")}
        actions={
          <div className="flex items-center gap-1 rounded-md border p-0.5 text-sm">
            {WINDOWS.map((w) => (
              <button
                key={w}
                type="button"
                onClick={() => setWindowDays(w)}
                className={cn(
                  "rounded px-2.5 py-1 transition-colors",
                  windowDays === w
                    ? "bg-primary text-primary-foreground"
                    : "hover:bg-accent",
                )}
              >
                {w} {t("analytics.dayShort")}
              </button>
            ))}
          </div>
        }
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              icon={Images}
              label={t("analytics.totalScans")}
              value={query.data.totals.batches}
            />
            <StatCard
              icon={Sprout}
              label={t("analytics.seedsDetected")}
              value={query.data.totals.detections}
            />
            <StatCard
              icon={CheckCircle2}
              label={t("analytics.goodRate")}
              value={query.data.totals.good_rate * 100}
              suffix="%"
            />
            <StatCard
              icon={Activity}
              label={t("analytics.goodBad")}
              value={query.data.totals.good}
              suffix={` / ${query.data.totals.bad}`}
            />
          </div>

          <TrendChart trend={query.data.trend} />

          <div className="grid gap-4 lg:grid-cols-2">
            <ConfidenceChart bins={query.data.confidence_histogram} />
            <TypeSplit rows={query.data.type_split} seedTypeName={seedTypeName} />
          </div>
        </div>
      )}
    </>
  );
}
