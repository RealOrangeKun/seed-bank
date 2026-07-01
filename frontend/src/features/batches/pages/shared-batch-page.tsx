import { Sprout } from "lucide-react";
import { useParams } from "react-router-dom";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState, LoadingState } from "@/components/shared/states";
import { StatusBadge } from "@/components/shared/status-badge";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { useI18n } from "@/i18n";
import { LanguageSwitcher } from "@/i18n/language-switcher";
import { formatDateTime, formatDuration, toNumber } from "@/lib/format";
import type { SharedBatchOut } from "../api";
import { useSharedBatch } from "../api";
import { verdictFor } from "../insights";

/** Flatten + tally detections across the shared batch's graph. */
function tally(batch: SharedBatchOut) {
  const dets = (batch.images ?? []).flatMap((img) =>
    (img.inferences ?? []).flatMap((inf) => inf.detections ?? []),
  );
  const good = dets.filter((d) => d.quality === "good").length;
  const bad = dets.filter((d) => d.quality === "bad").length;
  const classified = good + bad;
  const meanConf = dets.length
    ? dets.reduce((s, d) => s + toNumber(d.confidence), 0) / dets.length
    : 0;
  return {
    total: dets.length,
    good,
    bad,
    goodRate: classified ? good / classified : 0,
    meanConf,
  };
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border bg-card p-4 text-center">
      <div className="text-2xl font-bold tabular-nums">{value}</div>
      <div className="text-xs uppercase tracking-wide text-muted-foreground">{label}</div>
    </div>
  );
}

export function SharedBatchPage() {
  const { token = "" } = useParams();
  const query = useSharedBatch(token);
  const { t, tn } = useI18n();

  return (
    <div className="mx-auto min-h-screen max-w-3xl px-4 py-10">
      <header className="mb-6 flex items-center gap-2">
        <span className="rounded-md bg-primary/10 p-2 text-primary">
          <Sprout className="h-5 w-5" />
        </span>
        <div>
          <h1 className="text-lg font-semibold">{t("shared.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("shared.subtitle")}</p>
        </div>
        <div className="ms-auto flex items-center gap-1">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </header>

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <EmptyState
          title={t("shared.unavailableTitle")}
          description={t("shared.unavailableDesc")}
        />
      ) : (
        (() => {
          const batch = query.data;
          const tally_ = tally(batch);
          return (
            <div className="space-y-4">
              <Card>
                <CardContent className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs uppercase tracking-wide text-muted-foreground">
                      {t("shared.statStatus")}
                    </span>
                    <StatusBadge status={batch.status} />
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs uppercase tracking-wide text-muted-foreground">
                      {t("shared.statImages")}
                    </span>
                    <span className="text-sm font-medium">{batch.image_count}</span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs uppercase tracking-wide text-muted-foreground">
                      {t("shared.statSubmitted")}
                    </span>
                    <span className="text-sm font-medium">
                      {formatDateTime(batch.submitted_at)}
                    </span>
                  </div>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-xs uppercase tracking-wide text-muted-foreground">
                      {t("shared.statDuration")}
                    </span>
                    <span className="text-sm font-medium">
                      {formatDuration(batch.duration_ms)}
                    </span>
                  </div>
                </CardContent>
              </Card>

              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                <Stat label={t("shared.seeds")} value={`${tally_.total}`} />
                <Stat
                  label={t("shared.goodRate")}
                  value={`${Math.round(tally_.goodRate * 100)}%`}
                />
                <Stat label={t("shared.good")} value={`${tally_.good}`} />
                <Stat label={t("shared.bad")} value={`${tally_.bad}`} />
              </div>

              {(batch.images ?? []).map((img, i) => {
                const dets = (img.inferences ?? []).flatMap(
                  (inf) => inf.detections ?? [],
                );
                const good = dets.filter((d) => d.quality === "good").length;
                const bad = dets.filter((d) => d.quality === "bad").length;
                const classified = good + bad;
                const verdict = verdictFor(
                  classified ? good / classified : null,
                  batch.good_batch_threshold ?? 0.65,
                );
                return (
                  <Card key={img.id}>
                    <CardHeader className="pb-2">
                      <CardTitle className="flex items-center justify-between gap-2 text-base">
                        <span>{t("shared.imageN", { n: i + 1 })}</span>
                        <span className="flex items-center gap-2">
                          {verdict ? (
                            <span
                              className={
                                verdict === "good"
                                  ? "rounded-full bg-[hsl(var(--success))]/15 px-2.5 py-1 text-xs font-semibold text-[hsl(var(--success))]"
                                  : "rounded-full bg-destructive/15 px-2.5 py-1 text-xs font-semibold text-destructive"
                              }
                            >
                              {verdict === "good"
                                ? t("detail.verdictGood")
                                : t("detail.verdictBad")}
                            </span>
                          ) : null}
                          <Badge variant="secondary">{tn("seeds", dets.length)}</Badge>
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex h-3 overflow-hidden rounded-full bg-muted">
                        <div
                          className="bg-[hsl(var(--success))]"
                          style={{ width: `${dets.length ? (good / dets.length) * 100 : 0}%` }}
                        />
                        <div
                          className="bg-destructive"
                          style={{ width: `${dets.length ? (bad / dets.length) * 100 : 0}%` }}
                        />
                      </div>
                      <div className="mt-2 flex justify-between text-xs text-muted-foreground">
                        <span className="text-[hsl(var(--success))]">
                          {t("shared.goodLabel", { count: good })}
                        </span>
                        <span className="text-destructive">
                          {t("shared.badLabel", { count: bad })}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}

              <p className="pt-2 text-center text-xs text-muted-foreground">
                {t("shared.poweredBy")}
              </p>
            </div>
          );
        })()
      )}
    </div>
  );
}
