import { useState } from "react";

export interface PaginationState {
  page: number;
  pageSize: number;
  setPage: (page: number) => void;
  next: () => void;
  prev: () => void;
}

/** Local 1-indexed pagination state matching the API's page/page_size. */
export function usePagination(initialPageSize = 20): PaginationState {
  const [page, setPage] = useState(1);
  return {
    page,
    pageSize: initialPageSize,
    setPage,
    next: () => setPage((p) => p + 1),
    prev: () => setPage((p) => Math.max(1, p - 1)),
  };
}
