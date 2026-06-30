import { ArrowLeft } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { CopyButton } from "@/components/shared/copy-button";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { formatDateTime, humanize, shortId } from "@/lib/format";
import { isApiError } from "@/lib/api/errors";
import { MODEL_STATUS_TRANSITIONS } from "@/lib/api/types";
import type { ModelOut, ModelStatus } from "@/lib/api/types";

import { useModel, useModelPerformance, useUpdateModelStatus } from "../api";

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}

function PromoteCard({ model }: { model: ModelOut }) {
  const { t } = useI18n();
  // Only transitions the backend allows from the current state are offered.
  // A terminal state (e.g. `archived`) yields an empty list.
  const options = MODEL_STATUS_TRANSITIONS[model.status];
  const [target, setTarget] = useState<ModelStatus | undefined>(options[0]);
  const update = useUpdateModelStatus(model.id);

  const onUpdate = async () => {
    if (!target) return;
    try {
      const next = await update.mutateAsync(target);
      toast.success(t("models.statusSet", { status: humanize(next.status) }));
    } catch (err) {
      toast.error(isApiError(err) ? err.message : t("models.statusFailed"));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("models.lifecycle")}</CardTitle>
      </CardHeader>
      {options.length === 0 ? (
        <CardContent>
          <p className="text-sm text-muted-foreground">
            {t("models.terminalStatus", { status: humanize(model.status) })}
          </p>
        </CardContent>
      ) : (
        <CardContent className="flex flex-wrap items-end gap-3">
          <div className="space-y-1.5">
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
              {t("field.status")}
            </span>
            <Select value={target} onValueChange={(v) => setTarget(v as ModelStatus)}>
              <SelectTrigger className="w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {options.map((s) => (
                  <SelectItem key={s} value={s}>
                    {humanize(s)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={onUpdate} disabled={update.isPending || !target}>
            {update.isPending ? <Spinner /> : null}
            {t("models.updateStatus")}
          </Button>
        </CardContent>
      )}
    </Card>
  );
}

function PerformanceCard({ modelId }: { modelId: string }) {
  const { t } = useI18n();
  const query = useModelPerformance(modelId);
  const offlineMetrics = query.data?.offline_metrics ?? [];
  const rows = query.data?.rows ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("models.performance")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {query.isPending ? (
          <LoadingState />
        ) : query.isError ? (
          <ErrorState error={query.error} />
        ) : (
          <>
            {query.data?.note ? (
              <p className="rounded-md border border-dashed bg-card/50 p-3 text-sm text-muted-foreground">
                {query.data.note}
              </p>
            ) : null}

            <div className="space-y-2">
              <p className="text-xs uppercase tracking-wide text-muted-foreground">
                {t("models.offlineMetrics")}
              </p>
              {offlineMetrics.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("field.metric")}</TableHead>
                      <TableHead>{t("field.value")}</TableHead>
                      <TableHead>{t("field.dataset")}</TableHead>
                      <TableHead>{t("models.colComputed")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {offlineMetrics.map((m) => (
                      <TableRow key={`${m.metric_name}-${m.computed_at}`}>
                        <TableCell>{humanize(m.metric_name)}</TableCell>
                        <TableCell className="tabular-nums">{m.metric_value}</TableCell>
                        <TableCell className="font-mono text-xs">
                          {m.dataset_id ? shortId(m.dataset_id) : "—"}
                        </TableCell>
                        <TableCell className="text-muted-foreground">
                          {formatDateTime(m.computed_at)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground">
                  {t("models.noOfflineMetrics")}
                </p>
              )}
            </div>

            {rows.length > 0 ? (
              <div className="space-y-2">
                <p className="text-xs uppercase tracking-wide text-muted-foreground">
                  {t("models.online")}
                </p>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("field.model")}</TableHead>
                      <TableHead>{t("models.colCount")}</TableHead>
                      <TableHead>{t("models.colAvgLatency")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map((row, i) => {
                      const rowModelId = row["model_id"];
                      const n = row["n"];
                      const avgLatency = row["avg_latency_ms"];
                      return (
                        <TableRow key={i}>
                          <TableCell className="font-mono text-xs">
                            {typeof rowModelId === "string"
                              ? shortId(rowModelId)
                              : "—"}
                          </TableCell>
                          <TableCell className="tabular-nums">{String(n ?? "—")}</TableCell>
                          <TableCell className="tabular-nums">
                            {typeof avgLatency === "number"
                              ? `${avgLatency.toFixed(1)} ms`
                              : "—"}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            ) : null}
          </>
        )}
      </CardContent>
    </Card>
  );
}

export function ModelDetailPage() {
  const { t } = useI18n();
  const { modelId = "" } = useParams();
  const model = useModel(modelId);

  return (
    <>
      <PageHeader
        title={model.data ? `${model.data.name} ${model.data.version}` : t("models.detailFallback")}
        description={t("models.detailDescription")}
        actions={
          <Button variant="outline" asChild>
            <Link to="/models">
              <ArrowLeft className="h-4 w-4" /> {t("common.back")}
            </Link>
          </Button>
        }
      />

      {model.isPending ? (
        <LoadingState />
      ) : model.isError ? (
        <ErrorState error={model.error} />
      ) : (
        <>
          <Card>
            <CardContent className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-3">
              <MetaRow
                label={t("field.id")}
                value={
                  <span className="inline-flex items-center gap-1 font-mono text-xs">
                    {shortId(model.data.id)}
                    <CopyButton value={model.data.id} label={t("models.copyId")} />
                  </span>
                }
              />
              <MetaRow label={t("field.name")} value={model.data.name} />
              <MetaRow label={t("field.version")} value={model.data.version} />
              <MetaRow label={t("field.kind")} value={<Badge variant="outline">{humanize(model.data.kind)}</Badge>} />
              <MetaRow label={t("field.backend")} value={humanize(model.data.backend)} />
              <MetaRow label={t("field.status")} value={<StatusBadge status={model.data.status} />} />
              <MetaRow
                label={t("field.seedType")}
                value={
                  model.data.seed_type_id ? (
                    <span className="inline-flex items-center gap-1 font-mono text-xs">
                      {shortId(model.data.seed_type_id)}
                      <CopyButton value={model.data.seed_type_id} label={t("models.copySeedTypeId")} />
                    </span>
                  ) : (
                    "—"
                  )
                }
              />
              <MetaRow label={t("field.created")} value={formatDateTime(model.data.created_at)} />
              <MetaRow label={t("field.updated")} value={formatDateTime(model.data.updated_at)} />
              <MetaRow
                label={t("models.artifactUri")}
                value={
                  <span className="inline-flex items-center gap-1 break-all font-mono text-xs">
                    {model.data.artifact_uri}
                    <CopyButton value={model.data.artifact_uri} label={t("models.copyArtifactUri")} />
                  </span>
                }
              />
            </CardContent>
          </Card>

          <PromoteCard model={model.data} />
          <PerformanceCard modelId={modelId} />
        </>
      )}
    </>
  );
}
