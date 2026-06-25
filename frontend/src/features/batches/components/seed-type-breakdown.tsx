import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useI18n } from "@/i18n";

import type { SeedTypeBreakdown } from "../insights";

type Labeler = (id: string | null | undefined) => string;

/**
 * Stacked good/bad/unclassified bars per seed type. Surfaces the
 * already-computed `insights.bySeedType` (sorted by volume) so a reviewer can
 * see, at a glance, which crop graded worse. Pure presentational — the labeler
 * resolves seed-type ids to display names from the catalog.
 */
export function SeedTypeBreakdown({
  rows,
  seedTypeName,
}: {
  rows: SeedTypeBreakdown[];
  seedTypeName: Labeler;
}) {
  const { t, tn } = useI18n();
  if (rows.length === 0) return null;

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("breakdown.title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map((row) => {
          const total = row.total || 1;
          const goodPct = (row.good / total) * 100;
          const badPct = (row.bad / total) * 100;
          const unclPct = (row.unclassified / total) * 100;
          const classified = row.good + row.bad;
          const goodRate =
            classified > 0 ? Math.round((row.good / classified) * 100) : null;

          return (
            <div key={row.seedTypeId ?? "unclassified"} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">
                  {row.seedTypeId
                    ? seedTypeName(row.seedTypeId)
                    : t("breakdown.unclassified")}
                </span>
                <span className="text-xs text-muted-foreground">
                  {tn("seeds", row.total)}
                  {goodRate !== null ? t("breakdown.goodSuffix", { rate: goodRate }) : ""}
                </span>
              </div>
              <div className="flex h-2.5 overflow-hidden rounded-full bg-muted">
                <div
                  className="h-full bg-[hsl(var(--success))] transition-[width] duration-700 ease-out"
                  style={{ width: `${goodPct}%` }}
                  title={`${t("overlay.good")}: ${row.good}`}
                />
                <div
                  className="h-full bg-destructive transition-[width] duration-700 ease-out"
                  style={{ width: `${badPct}%` }}
                  title={`${t("overlay.bad")}: ${row.bad}`}
                />
                <div
                  className="h-full bg-muted-foreground/40 transition-[width] duration-700 ease-out"
                  style={{ width: `${unclPct}%` }}
                  title={`${t("breakdown.unclassified")}: ${row.unclassified}`}
                />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
