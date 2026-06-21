import { ArrowLeft, MapPin } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { BBoxOverlay } from "@/components/shared/bbox-overlay";
import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { CopyButton } from "@/components/shared/copy-button";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateTime, formatDuration, humanize, shortId } from "@/lib/format";
import type { ScanImageOut } from "@/lib/api/types";
import { useSeedTypes } from "@/features/catalog/api";
import { useModels } from "@/features/models/api";

import { useBatch, useBatchImageUrls } from "../api";

/** Resolve a seed-type id to its display name, falling back to a dash. */
type Labeler = (id: string | null | undefined) => string;

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}

function ImageCard({
  image,
  url,
  seedTypeName,
  modelName,
}: {
  image: ScanImageOut;
  url: string | undefined;
  seedTypeName: Labeler;
  modelName: Labeler;
}) {
  const inferences = image.inferences ?? [];
  const detections = inferences.flatMap((inf) => inf.detections ?? []);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="font-mono text-xs text-muted-foreground">
            {shortId(image.id)}
          </span>
          <Badge variant="secondary">{detections.length} detections</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {url ? (
          <BBoxOverlay src={url} detections={detections} alt={`Scan ${shortId(image.id)}`} />
        ) : (
          <Skeleton className="aspect-video w-full" />
        )}

        {inferences.length > 0 ? (
          <div className="space-y-3">
            {inferences.map((inf) => {
              const dets = inf.detections ?? [];
              return (
              <div key={inf.id} className="rounded-md border p-3">
                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="outline">{humanize(inf.backend)}</Badge>
                  <span className="inline-flex items-center gap-1">
                    {modelName(inf.model_id)}
                    <CopyButton value={inf.model_id} label="Copy model id" />
                  </span>
                  <span>·</span>
                  <span>{formatDuration(inf.latency_ms)}</span>
                  {inf.error ? (
                    <span className="text-destructive">· {inf.error}</span>
                  ) : null}
                </div>
                {dets.length > 0 ? (
                  <Table className="mt-2">
                    <TableHeader>
                      <TableRow>
                        <TableHead>Seed type</TableHead>
                        <TableHead>Quality</TableHead>
                        <TableHead>Confidence</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dets.map((d) => (
                        <TableRow key={d.id}>
                          <TableCell>{seedTypeName(d.seed_type_id)}</TableCell>
                          <TableCell>
                            {d.quality ? <StatusBadge status={d.quality} /> : "—"}
                          </TableCell>
                          <TableCell>
                            <ConfidenceBadge value={d.confidence} />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                ) : (
                  <p className="mt-2 text-sm text-muted-foreground">No seeds detected.</p>
                )}
              </div>
              );
            })}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function BatchDetailPage() {
  const { batchId = "" } = useParams();
  const batch = useBatch(batchId);
  const isTerminal =
    batch.data && ["succeeded", "partial", "failed"].includes(batch.data.status);
  const imageUrls = useBatchImageUrls(batchId, Boolean(isTerminal));

  const seedTypes = useSeedTypes();
  const models = useModels({ page: 1, pageSize: 100 });

  const urlMap = new Map((imageUrls.data ?? []).map((u) => [u.image_id, u.url]));
  const seedTypeMap = new Map((seedTypes.data ?? []).map((s) => [s.id, s.display_name]));
  const modelMap = new Map(
    (models.data?.data ?? []).map((m) => [m.id, `${m.name} ${m.version}`]),
  );
  const seedTypeName: Labeler = (id) => (id ? (seedTypeMap.get(id) ?? "Unclassified") : "—");
  const modelName: Labeler = (id) => (id ? (modelMap.get(id) ?? `model ${shortId(id)}`) : "—");

  const title = batch.data
    ? `Scan · ${formatDateTime(batch.data.submitted_at)}`
    : "Scan";

  return (
    <>
      <PageHeader
        title={title}
        description="Detection and quality results."
        actions={
          <Button variant="outline" asChild>
            <Link to="/batches">
              <ArrowLeft className="h-4 w-4" /> Back
            </Link>
          </Button>
        }
      />

      {batch.isPending ? (
        <LoadingState />
      ) : batch.isError ? (
        <ErrorState error={batch.error} />
      ) : (
        <>
          <Card>
            <CardContent className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">
              <MetaRow label="Status" value={<StatusBadge status={batch.data.status} />} />
              <MetaRow label="Images" value={batch.data.image_count} />
              <MetaRow
                label="Submitted"
                value={formatDateTime(batch.data.submitted_at)}
              />
              <MetaRow label="Duration" value={formatDuration(batch.data.duration_ms)} />
              <MetaRow
                label="Scan ID"
                value={
                  <span className="inline-flex items-center gap-1 font-mono text-xs">
                    {shortId(batch.data.id)}
                    <CopyButton value={batch.data.id} label="Copy scan id" />
                  </span>
                }
              />
              {batch.data.geo_country_code ? (
                <MetaRow
                  label="Location"
                  value={
                    <span className="inline-flex items-center gap-1">
                      <MapPin className="h-3.5 w-3.5" />
                      {batch.data.geo_city
                        ? `${batch.data.geo_city}, ${batch.data.geo_country_code}`
                        : batch.data.geo_country_code}
                    </span>
                  }
                />
              ) : null}
            </CardContent>
          </Card>

          {batch.data.error_message ? (
            <Card className="border-destructive/40">
              <CardContent className="p-4 text-sm text-destructive">
                {batch.data.error_message}
              </CardContent>
            </Card>
          ) : null}

          {!isTerminal ? (
            <Card>
              <CardContent className="flex items-center gap-3 p-5 text-sm text-muted-foreground">
                <Spinner className="text-primary" />
                Analysis in progress — this page updates automatically.
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 lg:grid-cols-2">
              {(batch.data.images ?? []).map((image) => (
                <ImageCard
                  key={image.id}
                  image={image}
                  url={urlMap.get(image.id)}
                  seedTypeName={seedTypeName}
                  modelName={modelName}
                />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
