import { ArrowLeft } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { CopyButton } from "@/components/shared/copy-button";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useI18n } from "@/i18n";
import { formatDateTime, formatDuration, shortId } from "@/lib/format";

import { useExperiment } from "../api";

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}

function IdValue({ id }: { id: string }) {
  const { t } = useI18n();
  return (
    <span className="inline-flex items-center gap-1 font-mono text-xs">
      {shortId(id)}
      <CopyButton value={id} label={t("experiments.copyId")} />
    </span>
  );
}

function renderMetric(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

export function ExperimentDetailPage() {
  const { t } = useI18n();
  const { experimentId = "" } = useParams();
  const experiment = useExperiment(experimentId);
  const isTerminal =
    experiment.data && ["succeeded", "failed"].includes(experiment.data.status);

  const metrics = Object.entries(experiment.data?.summary_metrics ?? {});

  return (
    <>
      <PageHeader
        title={
          experiment.data?.name ??
          t("experiments.detailFallback", { id: shortId(experimentId) })
        }
        description={t("experiments.detailDescription")}
        actions={
          <Button variant="outline" asChild>
            <Link to="/experiments">
              <ArrowLeft className="h-4 w-4" /> {t("common.back")}
            </Link>
          </Button>
        }
      />

      {experiment.isPending ? (
        <LoadingState />
      ) : experiment.isError ? (
        <ErrorState error={experiment.error} />
      ) : (
        <>
          <Card>
            <CardContent className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-3">
              <MetaRow
                label={t("field.status")}
                value={<StatusBadge status={experiment.data.status} />}
              />
              <MetaRow label={t("field.model")} value={<IdValue id={experiment.data.model_id} />} />
              <MetaRow
                label={t("field.dataset")}
                value={<IdValue id={experiment.data.dataset_id} />}
              />
              <MetaRow
                label={t("experiments.metaStarted")}
                value={formatDateTime(experiment.data.started_at) || "—"}
              />
              <MetaRow
                label={t("experiments.metaFinished")}
                value={formatDateTime(experiment.data.finished_at) || "—"}
              />
              <MetaRow
                label={t("field.duration")}
                value={formatDuration(experiment.data.duration_ms)}
              />
              <MetaRow label={t("experiments.metaResults")} value={experiment.data.result_count} />
            </CardContent>
          </Card>

          {!isTerminal ? (
            <Card>
              <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
                <Spinner className="text-primary" />
                {t("experiments.inProgress")}
              </CardContent>
            </Card>
          ) : metrics.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t("experiments.summaryMetrics")}</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("field.metric")}</TableHead>
                      <TableHead>{t("field.value")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {metrics.map(([key, value]) => (
                      <TableRow key={key}>
                        <TableCell className="font-medium">{key}</TableCell>
                        <TableCell className="font-mono text-xs">
                          {renderMetric(value)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : null}
        </>
      )}
    </>
  );
}
