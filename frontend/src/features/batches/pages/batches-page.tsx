import { ScanLine } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";

import { PageHeader } from "@/components/shared/page-header";
import { Pagination } from "@/components/shared/pagination";
import { StatusBadge } from "@/components/shared/status-badge";
import { EmptyState, ErrorState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatDateTime, formatDuration, shortId } from "@/lib/format";
import { usePagination } from "@/hooks/use-pagination";

import { useBatches } from "../api";

export function BatchesPage() {
  const navigate = useNavigate();
  const pagination = usePagination(20);
  const query = useBatches({ page: pagination.page, pageSize: pagination.pageSize });

  return (
    <>
      <PageHeader
        title="Scan history"
        description="Every batch you've submitted for analysis."
        actions={
          <Button asChild>
            <Link to="/analyze">
              <ScanLine className="h-4 w-4" /> New analysis
            </Link>
          </Button>
        }
      />

      {query.isPending ? (
        <LoadingState />
      ) : query.isError ? (
        <ErrorState error={query.error} />
      ) : query.data.data.length === 0 ? (
        <EmptyState
          title="No scans yet"
          description="Upload seed images to run detection and quality classification."
          action={
            <Button asChild>
              <Link to="/analyze">Start a scan</Link>
            </Button>
          }
        />
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Batch</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Images</TableHead>
                  <TableHead>Submitted</TableHead>
                  <TableHead>Duration</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {query.data.data.map((b) => (
                  <TableRow
                    key={b.id}
                    className="cursor-pointer"
                    onClick={() => navigate(`/batches/${b.id}`)}
                  >
                    <TableCell className="font-mono text-xs">{shortId(b.id)}</TableCell>
                    <TableCell>
                      <StatusBadge status={b.status} />
                    </TableCell>
                    <TableCell>{b.image_count}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {formatDateTime(b.submitted_at)}
                    </TableCell>
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
    </>
  );
}
