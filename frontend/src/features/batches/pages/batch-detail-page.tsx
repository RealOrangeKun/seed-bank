import { ArrowLeft, Check, Copy, Download, MapPin, Share2, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";

import { BBoxOverlay } from "@/components/shared/bbox-overlay";
import { ConfidenceBadge } from "@/components/shared/confidence-badge";
import { CopyButton } from "@/components/shared/copy-button";
import { PageHeader } from "@/components/shared/page-header";
import { StatusBadge } from "@/components/shared/status-badge";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
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
import { useI18n } from "@/i18n";
import { formatDateTime, formatDuration, humanize, shortId } from "@/lib/format";
import type { ScanImageOut } from "@/lib/api/types";
import { useSeedTypes } from "@/features/catalog/api";
import { useModels } from "@/features/models/api";

import {
  downloadBatchExport,
  useBatch,
  useBatchImageUrls,
  useCreateShare,
  useDeleteBatch,
  useRevokeShare,
} from "../api";
import { AnalyzingIndicator } from "../components/analyzing-indicator";
import { InsightsPanel } from "../components/insights-panel";
import { OverlayControls, type QualityKey } from "../components/overlay-controls";
import { SeedTypeBreakdown } from "../components/seed-type-breakdown";
import { computeInsights } from "../insights";

/** Resolve a seed-type id to its display name, falling back to a dash. */
type Labeler = (id: string | null | undefined) => string;

const ALL_QUALITIES: QualityKey[] = ["good", "bad", "unclassified"];

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
  const { t, tn } = useI18n();
  const inferences = image.inferences ?? [];
  const detections = inferences.flatMap((inf) => inf.detections ?? []);

  // Per-image overlay controls — each scan filters independently.
  const [active, setActive] = useState<Set<QualityKey>>(() => new Set(ALL_QUALITIES));
  const [minConfidence, setMinConfidence] = useState(0);
  const [showLabels, setShowLabels] = useState(false);

  const toggleQuality = (key: QualityKey) =>
    setActive((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });

  const visibleCount = detections.filter((d) => {
    const conf = Number.parseFloat(String(d.confidence));
    const key = (d.quality ?? "unclassified") as QualityKey;
    return conf >= minConfidence && active.has(key);
  }).length;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span className="font-mono text-xs text-muted-foreground">
            {shortId(image.id)}
          </span>
          <Badge variant="secondary">{tn("detections", detections.length)}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {url ? (
          <>
            <BBoxOverlay
              src={url}
              detections={detections}
              alt={`Scan ${shortId(image.id)}`}
              minConfidence={minConfidence}
              qualityFilter={active as Set<string>}
              showLabels={showLabels}
            />
            {detections.length > 0 ? (
              <OverlayControls
                active={active}
                onToggleQuality={toggleQuality}
                minConfidence={minConfidence}
                onMinConfidenceChange={setMinConfidence}
                showLabels={showLabels}
                onToggleLabels={() => setShowLabels((s) => !s)}
                visibleCount={visibleCount}
                totalCount={detections.length}
              />
            ) : null}
          </>
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
                      <CopyButton value={inf.model_id} label={t("detail.copyModelId")} />
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
                          <TableHead>{t("detail.colSeedType")}</TableHead>
                          <TableHead>{t("detail.colQuality")}</TableHead>
                          <TableHead>{t("detail.colConfidence")}</TableHead>
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
                    <p className="mt-2 text-sm text-muted-foreground">
                      {t("detail.noSeedsDetected")}
                    </p>
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
  const navigate = useNavigate();
  const { t } = useI18n();
  const batch = useBatch(batchId);
  const isTerminal =
    batch.data && ["succeeded", "partial", "failed"].includes(batch.data.status);
  const imageUrls = useBatchImageUrls(batchId, Boolean(isTerminal));

  const seedTypes = useSeedTypes();
  const models = useModels({ page: 1, pageSize: 100 });
  const deleteBatch = useDeleteBatch();
  const createShare = useCreateShare();
  const revokeShare = useRevokeShare();

  const [confirmOpen, setConfirmOpen] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [shareOpen, setShareOpen] = useState(false);
  const [shareUrl, setShareUrl] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const urlMap = new Map((imageUrls.data ?? []).map((u) => [u.image_id, u.url]));
  const seedTypeMap = new Map((seedTypes.data ?? []).map((s) => [s.id, s.display_name]));
  const modelMap = new Map(
    (models.data?.data ?? []).map((m) => [m.id, `${m.name} ${m.version}`]),
  );
  const seedTypeName: Labeler = (id) =>
    id ? (seedTypeMap.get(id) ?? t("detail.unclassified")) : "—";
  const modelName: Labeler = (id) =>
    id ? (modelMap.get(id) ?? t("detail.modelFallback", { id: shortId(id) })) : "—";

  const insights = batch.data ? computeInsights(batch.data) : null;
  const hasDetections = insights ? insights.total > 0 : false;

  const title = batch.data
    ? t("detail.titleDated", { date: formatDateTime(batch.data.submitted_at) })
    : t("detail.title");

  async function handleExport(format: "csv" | "json") {
    setExporting(true);
    try {
      await downloadBatchExport(batchId, format);
      toast.success(t("detail.exported", { format: format.toUpperCase() }));
    } catch {
      toast.error(t("detail.exportFailed"));
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    try {
      await deleteBatch.mutateAsync(batchId);
      toast.success(t("detail.deleted"));
      navigate("/batches");
    } catch {
      toast.error(t("detail.deleteFailed"));
    }
  }

  async function handleShare() {
    try {
      const link = await createShare.mutateAsync(batchId);
      setShareUrl(`${window.location.origin}/shared/${link.share_token}`);
      setShareOpen(true);
    } catch {
      toast.error(t("share.createFailed"));
    }
  }

  async function handleRevokeShare() {
    try {
      await revokeShare.mutateAsync(batchId);
      setShareUrl(null);
      setShareOpen(false);
      toast.success(t("share.revoked"));
    } catch {
      toast.error(t("share.revokeFailed"));
    }
  }

  function copyShareUrl() {
    if (!shareUrl) return;
    void navigator.clipboard.writeText(shareUrl);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
    toast.success(t("share.linkCopied"));
  }

  return (
    <>
      <PageHeader
        title={title}
        description={t("detail.description")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" asChild>
              <Link to="/batches">
                <ArrowLeft className="h-4 w-4" /> {t("common.back")}
              </Link>
            </Button>
            {isTerminal && hasDetections ? (
              <>
                <Button
                  variant="outline"
                  onClick={handleShare}
                  disabled={createShare.isPending}
                >
                  {createShare.isPending ? <Spinner /> : <Share2 className="h-4 w-4" />}
                  {t("share.button")}
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" disabled={exporting}>
                      {exporting ? <Spinner /> : <Download className="h-4 w-4" />}
                      {t("detail.export")}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem onClick={() => handleExport("csv")}>
                      {t("detail.downloadCsv")}
                    </DropdownMenuItem>
                    <DropdownMenuItem onClick={() => handleExport("json")}>
                      {t("detail.downloadJson")}
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </>
            ) : null}
            <Button
              variant="outline"
              className="text-destructive hover:text-destructive"
              onClick={() => setConfirmOpen(true)}
            >
              <Trash2 className="h-4 w-4" /> {t("common.delete")}
            </Button>
          </div>
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
              <MetaRow
                label={t("detail.metaStatus")}
                value={<StatusBadge status={batch.data.status} />}
              />
              <MetaRow label={t("detail.metaImages")} value={batch.data.image_count} />
              <MetaRow
                label={t("detail.metaSubmitted")}
                value={formatDateTime(batch.data.submitted_at)}
              />
              <MetaRow
                label={t("detail.metaDuration")}
                value={formatDuration(batch.data.duration_ms)}
              />
              <MetaRow
                label={t("detail.metaScanId")}
                value={
                  <span className="inline-flex items-center gap-1 font-mono text-xs">
                    {shortId(batch.data.id)}
                    <CopyButton value={batch.data.id} label={t("detail.copyScanId")} />
                  </span>
                }
              />
              {batch.data.geo_country_code ? (
                <MetaRow
                  label={t("detail.metaLocation")}
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
            <AnalyzingIndicator pending={batch.data.status === "pending"} />
          ) : (
            <>
              {insights && hasDetections ? (
                <>
                  <InsightsPanel insights={insights} />
                  {insights.bySeedType.length > 1 ? (
                    <SeedTypeBreakdown
                      rows={insights.bySeedType}
                      seedTypeName={seedTypeName}
                    />
                  ) : null}
                </>
              ) : null}
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
            </>
          )}
        </>
      )}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("detail.deleteDialogTitle")}</DialogTitle>
            <DialogDescription>{t("detail.deleteDialogDesc")}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">{t("common.cancel")}</Button>
            </DialogClose>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteBatch.isPending}
            >
              {deleteBatch.isPending ? <Spinner /> : <Trash2 className="h-4 w-4" />}
              {t("common.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={shareOpen} onOpenChange={setShareOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Share2 className="h-5 w-5 text-primary" />
              {t("share.title")}
            </DialogTitle>
            <DialogDescription>{t("share.description")}</DialogDescription>
          </DialogHeader>
          {shareUrl ? (
            <div className="space-y-3">
              <div className="flex items-center gap-2 rounded-md border bg-muted/40 p-2">
                <code className="flex-1 truncate font-mono text-xs" dir="ltr">
                  {shareUrl}
                </code>
                <Button type="button" size="sm" variant="secondary" onClick={copyShareUrl}>
                  {copied ? (
                    <Check className="h-4 w-4 text-success" />
                  ) : (
                    <Copy className="h-4 w-4" />
                  )}
                  {copied ? t("share.copied") : t("share.copyLink")}
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">{t("share.activeNote")}</p>
            </div>
          ) : null}
          <DialogFooter>
            <Button
              variant="outline"
              className="text-destructive hover:text-destructive"
              onClick={handleRevokeShare}
              disabled={revokeShare.isPending}
            >
              {revokeShare.isPending ? <Spinner /> : null}
              {t("share.revoke")}
            </Button>
            <DialogClose asChild>
              <Button>{t("common.done")}</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
