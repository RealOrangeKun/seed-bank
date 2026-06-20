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
      toast.error("Paste at least one image storage key.");
      return;
    }
    try {
      const result = await add.mutateAsync(keys);
      toast.success(`Added ${result.added} item${result.added === 1 ? "" : "s"}.`);
      setText("");
      setOpen(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Failed to add items.");
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
          <Plus className="h-4 w-4" /> Add items
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add items</DialogTitle>
          <DialogDescription>
            Paste one image storage key per line. Keys reference objects already
            uploaded to MinIO.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-4">
          <Field
            id="storageKeys"
            label="Image storage keys"
            hint={keys.length > 0 ? `${keys.length} key${keys.length === 1 ? "" : "s"}` : "One per line"}
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
              Add {keys.length > 0 ? `${keys.length} item${keys.length === 1 ? "" : "s"}` : "items"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export function DatasetDetailPage() {
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
        title={dataset.data ? dataset.data.name : `Dataset ${shortId(datasetId)}`}
        description="Images and ground truth used for offline evaluation."
        actions={
          <div className="flex items-center gap-2">
            <AddItemsDialog datasetId={datasetId} />
            <Button variant="outline" asChild>
              <Link to="/datasets">
                <ArrowLeft className="h-4 w-4" /> Back
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
              label="ID"
              value={
                <span className="inline-flex items-center gap-1 font-mono text-xs">
                  {shortId(dataset.data.id)}
                  <CopyButton value={dataset.data.id} label="Copy dataset id" />
                </span>
              }
            />
            <MetaRow label="Items" value={dataset.data.item_count} />
            <MetaRow label="Created" value={formatDateTime(dataset.data.created_at)} />
            <MetaRow label="Updated" value={formatDateTime(dataset.data.updated_at)} />
            {dataset.data.description ? (
              <MetaRow
                label="Description"
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
          title="No items yet"
          description="Add image storage keys to populate this dataset."
          action={<AddItemsDialog datasetId={datasetId} />}
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Image storage key</TableHead>
                  <TableHead>Checksum</TableHead>
                  <TableHead>Ground truth</TableHead>
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
