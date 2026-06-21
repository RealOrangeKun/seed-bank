import { GitCompareArrows } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";

import { PageHeader } from "@/components/shared/page-header";
import { ErrorState, LoadingState } from "@/components/shared/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { useBatches } from "@/features/batches/api";
import { formatDateTime, shortId } from "@/lib/format";
import { usePagination } from "@/hooks/use-pagination";

import { useCompareBatches, type BatchCompareRow } from "../api";

const MAX = 10;

/** A single metric row in the side-by-side table; finds the best column. */
function metricRow(
  label: string,
  rows: BatchCompareRow[],
  pick: (r: BatchCompareRow) => number,
  fmt: (n: number) => string,
  higherIsBetter = true,
) {
  const values = rows.map(pick);
  const best = higherIsBetter ? Math.max(...values) : Math.min(...values);
  return (
    <TableRow>
      <TableCell className="font-medium text-muted-foreground">{label}</TableCell>
      {rows.map((r) => {
        const v = pick(r);
        const isBest =
          rows.length > 1 && v === best && values.filter((x) => x === best).length === 1;
        return (
          <TableCell
            key={r.batch_id}
            className={isBest ? "font-semibold text-primary" : ""}
          >
            {fmt(v)}
          </TableCell>
        );
      })}
    </TableRow>
  );
}

export function ComparePage() {
  const pagination = usePagination(20);
  const history = useBatches({ page: pagination.page, pageSize: pagination.pageSize });
  const compare = useCompareBatches();
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const rows = history.data?.data ?? [];

  function toggle(id: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < MAX) next.add(id);
      else toast.error(`Compare up to ${MAX} scans.`);
      return next;
    });
  }

  async function runCompare() {
    if (selected.size < 2) {
      toast.error("Pick at least 2 scans to compare.");
      return;
    }
    try {
      await compare.mutateAsync([...selected]);
    } catch {
      toast.error("Compare failed.");
    }
  }

  const result = compare.data;

  return (
    <>
      <PageHeader
        title="Compare scans"
        description="Pick 2–10 scans to see their results side by side."
        actions={
          <Button onClick={runCompare} disabled={compare.isPending || selected.size < 2}>
            {compare.isPending ? <Spinner /> : <GitCompareArrows className="h-4 w-4" />}
            Compare ({selected.size})
          </Button>
        }
      />

      {history.isPending ? (
        <LoadingState />
      ) : history.isError ? (
        <ErrorState error={history.error} />
      ) : (
        <div className="space-y-4">
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-10" />
                    <TableHead>Scan</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Images</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((b) => (
                    <TableRow
                      key={b.id}
                      className="cursor-pointer"
                      onClick={() => toggle(b.id)}
                    >
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          checked={selected.has(b.id)}
                          onChange={() => toggle(b.id)}
                          aria-label={`Select scan ${b.id}`}
                          className="cursor-pointer accent-[hsl(var(--primary))]"
                        />
                      </TableCell>
                      <TableCell className="font-medium">
                        {formatDateTime(b.submitted_at)}
                      </TableCell>
                      <TableCell className="capitalize text-muted-foreground">
                        {b.status}
                      </TableCell>
                      <TableCell>{b.image_count}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          {result && result.rows.length > 0 ? (
            <Card>
              <CardContent className="overflow-x-auto p-0">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Metric</TableHead>
                      {result.rows.map((r) => (
                        <TableHead key={r.batch_id} className="font-mono text-xs">
                          {shortId(r.batch_id)}
                        </TableHead>
                      ))}
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {metricRow(
                      "Images",
                      result.rows,
                      (r) => r.images,
                      (n) => `${n}`,
                    )}
                    {metricRow(
                      "Seeds detected",
                      result.rows,
                      (r) => r.detections,
                      (n) => `${n}`,
                    )}
                    {metricRow(
                      "Good",
                      result.rows,
                      (r) => r.good,
                      (n) => `${n}`,
                    )}
                    {metricRow(
                      "Bad",
                      result.rows,
                      (r) => r.bad,
                      (n) => `${n}`,
                      false,
                    )}
                    {metricRow(
                      "Good rate",
                      result.rows,
                      (r) => r.good_rate,
                      (n) => `${(n * 100).toFixed(1)}%`,
                    )}
                    {metricRow(
                      "Mean confidence",
                      result.rows,
                      (r) => r.mean_confidence,
                      (n) => `${(n * 100).toFixed(1)}%`,
                    )}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          ) : null}
        </div>
      )}
    </>
  );
}
