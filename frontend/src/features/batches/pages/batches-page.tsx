import { ScanLine, Trash2 } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { formatDateTime, formatDuration } from "@/lib/format";
import { usePagination } from "@/hooks/use-pagination";

import { useBatches, useBulkDeleteBatches } from "../api";

export function BatchesPage() {
  const navigate = useNavigate();
  const { t, tn } = useI18n();
  const pagination = usePagination(20);
  const query = useBatches({ page: pagination.page, pageSize: pagination.pageSize });
  const bulkDelete = useBulkDeleteBatches();

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [confirmOpen, setConfirmOpen] = useState(false);

  const rows = query.data?.data ?? [];
  const allOnPageSelected = rows.length > 0 && rows.every((b) => selected.has(b.id));

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  function toggleAll() {
    setSelected((prev) => {
      if (allOnPageSelected) {
        const next = new Set(prev);
        rows.forEach((b) => next.delete(b.id));
        return next;
      }
      return new Set([...prev, ...rows.map((b) => b.id)]);
    });
  }

  async function handleBulkDelete() {
    try {
      const count = await bulkDelete.mutateAsync([...selected]);
      toast.success(tn("deletedScans", count));
      setSelected(new Set());
      setConfirmOpen(false);
    } catch {
      toast.error(t("batches.bulkDeleteFailed"));
    }
  }

  return (
    <>
      <PageHeader
        title={t("batches.title")}
        description={t("batches.description")}
        actions={
          <div className="flex items-center gap-2">
            {selected.size > 0 ? (
              <Button
                variant="outline"
                className="text-destructive hover:text-destructive"
                onClick={() => setConfirmOpen(true)}
              >
                <Trash2 className="h-4 w-4" /> {tn("deleteScans", selected.size)}
              </Button>
            ) : null}
            <Button asChild>
              <Link to="/analyze">
                <ScanLine className="h-4 w-4" /> {t("batches.newAnalysis")}
              </Link>
            </Button>
          </div>
        }
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : rows.length === 0 ? (
        <EmptyState
          title={t("batches.noScansTitle")}
          description={t("batches.noScansDesc")}
          action={
            <Button asChild>
              <Link to="/analyze">{t("batches.startScan")}</Link>
            </Button>
          }
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input
                      type="checkbox"
                      checked={allOnPageSelected}
                      onChange={toggleAll}
                      aria-label={t("batches.selectAll")}
                      className="cursor-pointer accent-[hsl(var(--primary))]"
                    />
                  </TableHead>
                  <TableHead>{t("batches.colScan")}</TableHead>
                  <TableHead>{t("batches.colStatus")}</TableHead>
                  <TableHead>{t("batches.colImages")}</TableHead>
                  <TableHead>{t("batches.colDuration")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((b) => (
                  <TableRow
                    key={b.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/batches/${b.id}`)}
                  >
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected.has(b.id)}
                        onChange={() => toggle(b.id)}
                        aria-label={t("batches.colScan")}
                        className="cursor-pointer accent-[hsl(var(--primary))]"
                      />
                    </TableCell>
                    <TableCell className="font-medium">
                      {formatDateTime(b.submitted_at)}
                    </TableCell>
                    <TableCell>
                      <StatusBadge status={b.status} />
                    </TableCell>
                    <TableCell>{b.image_count}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDuration(b.duration_ms)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {query.data ? (
        <Pagination meta={query.data.meta} onPageChange={pagination.setPage} />
      ) : null}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{tn("deleteScansTitle", selected.size)}</DialogTitle>
            <DialogDescription>{t("batches.deleteDialogDesc")}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">{t("common.cancel")}</Button>
            </DialogClose>
            <Button
              variant="destructive"
              onClick={handleBulkDelete}
              disabled={bulkDelete.isPending}
            >
              {bulkDelete.isPending ? <Spinner /> : <Trash2 className="h-4 w-4" />}
              {t("common.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
