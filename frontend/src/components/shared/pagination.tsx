import { ChevronLeft, ChevronRight } from "lucide-react";

import { Button } from "@/components/ui/button";
import { useI18n } from "@/i18n";
import type { PageMeta } from "@/lib/api/types";

interface PaginationProps {
  meta: PageMeta | undefined;
  onPageChange: (page: number) => void;
}

/** Page x of y with prev/next, driven by the API's PageMeta. */
export function Pagination({ meta, onPageChange }: PaginationProps) {
  const { t, dir } = useI18n();
  if (!meta) return null;
  const totalPages = Math.max(1, Math.ceil(meta.total / meta.page_size));
  const start = meta.total === 0 ? 0 : (meta.page - 1) * meta.page_size + 1;
  const end = Math.min(meta.page * meta.page_size, meta.total);

  // In RTL "previous" points right and "next" points left.
  const PrevIcon = dir === "rtl" ? ChevronRight : ChevronLeft;
  const NextIcon = dir === "rtl" ? ChevronLeft : ChevronRight;

  return (
    <div className="flex items-center justify-between gap-4 pt-2 text-sm text-muted-foreground">
      <span>{t("pagination.range", { start, end, total: meta.total })}</span>
      <div className="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={meta.page <= 1}
          onClick={() => onPageChange(meta.page - 1)}
        >
          <PrevIcon className="h-4 w-4" /> {t("pagination.prev")}
        </Button>
        <span className="tabular-nums">
          {meta.page} / {totalPages}
        </span>
        <Button
          variant="outline"
          size="sm"
          disabled={!meta.has_more}
          onClick={() => onPageChange(meta.page + 1)}
        >
          {t("pagination.next")} <NextIcon className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
