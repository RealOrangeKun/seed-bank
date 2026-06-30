import { ArrowLeft, Plus } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";

import { CopyButton } from "@/components/shared/copy-button";
import { Field } from "@/components/shared/field";
import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
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
import { usePagination } from "@/hooks/use-pagination";
import { formatDateTime, shortId } from "@/lib/format";

import { useAddDatasetItems, useDataset, useDatasetItems } from "../api";

function MetaRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="text-sm font-medium">{value}</dd>
    </div>
  );
}

function AddItemsDialog({ datasetId }: { datasetId: string }) {
  const { t, tn } = useI18n();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const add = useAddDatasetItems(datasetId);

  const keys = text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0);

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (keys.length === 0) {
      toast.error(t("datasets.pasteAtLeastOne"));
      return;
    }
    try {
      const result = await add.mutateAsync(keys);
      toast.success(tn("datasetItemsAdded", result.added));
      setText("");
      setOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t("datasets.addFailed"));
    }
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setText("");
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <Plus className="h-4 w-4" /> {t("datasets.addItems")}
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("datasets.addItems")}</DialogTitle>
          <DialogDescription>{t("datasets.addItemsDesc")}</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field
            id="storageKeys"
            label={t("datasets.storageKeysLabel")}
            hint={keys.length > 0 ? tn("datasetKeys", keys.length) : t("datasets.onePerLine")}
          >
            <textarea
              id="storageKeys"
              value={text}
              onChange={(e) => setText(e.target.value)}
              rows={8}
              placeholder={"datasets/maize/0001.jpg\ndatasets/maize/0002.jpg"}
              className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 font-mono text-sm shadow-sm transition-colors placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
            />
          </Field>
          <DialogFooter>
            <Button type="submit" disabled={add.isPending}>
              {add.isPending ? <Spinner /> : null}
              {keys.length > 0 ? tn("datasetAddBtn", keys.length) : t("datasets.addItems")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function DatasetDetailPage() {
  const { t } = useI18n();
  const { datasetId = "" } = useParams();
  const pagination = usePagination(20);
  const dataset = useDataset(datasetId);
  const items = useDatasetItems(datasetId, {
    page: pagination.page,
    pageSize: pagination.pageSize,
  });

  return (
    <>
      <PageHeader
        title={
          dataset.data
            ? dataset.data.name
            : t("datasets.detailFallback", { id: shortId(datasetId) })
        }
        description={t("datasets.detailDescription")}
        actions={
          <div className="flex items-center gap-2">
            <AddItemsDialog datasetId={datasetId} />
            <Button variant="outline" asChild>
              <Link to="/datasets">
                <ArrowLeft className="h-4 w-4" /> {t("common.back")}
              </Link>
            </Button>
          </div>
        }
      />

      {dataset.isPending ? (
        <LoadingState />
      ) : dataset.isError ? (
        <ErrorState error={dataset.error} />
      ) : (
        <Card>
          <CardContent className="grid grid-cols-2 gap-4 p-5 sm:grid-cols-4">
            <MetaRow
              label={t("field.id")}
              value={
                <span className="inline-flex items-center gap-1 font-mono text-xs">
                  {shortId(dataset.data.id)}
                  <CopyButton value={dataset.data.id} label={t("datasets.copyId")} />
                </span>
              }
            />
            <MetaRow label={t("field.items")} value={dataset.data.item_count} />
            <MetaRow label={t("field.created")} value={formatDateTime(dataset.data.created_at)} />
            <MetaRow label={t("field.updated")} value={formatDateTime(dataset.data.updated_at)} />
            {dataset.data.description ? (
              <MetaRow
                label={t("field.description")}
                value={<span className="font-normal">{dataset.data.description}</span>}
              />
            ) : null}
          </CardContent>
        </Card>
      )}

      {items.isPending ? (
        <LoadingState />
      ) : items.isError ? (
        <ErrorState error={items.error} />
      ) : items.data.data.length === 0 ? (
        <EmptyState
          title={t("datasets.itemsEmpty")}
          description={t("datasets.itemsEmptyDesc")}
          action={<AddItemsDialog datasetId={datasetId} />}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("datasets.colStorageKey")}</TableHead>
                  <TableHead>{t("datasets.colChecksum")}</TableHead>
                  <TableHead>{t("datasets.colGroundTruth")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.data.data.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="font-mono text-xs">
                      {item.image_storage_key}
                    </TableCell>
                    <TableCell className="font-mono text-xs text-muted-foreground">
                      {item.checksum ?? "—"}
                    </TableCell>
                    <TableCell>
                      {item.ground_truth ? (
                        <Badge variant="secondary">JSON</Badge>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {items.data ? (
        <Pagination meta={items.data.meta} onPageChange={pagination.setPage} />
      ) : null}
    </>
  );
}
