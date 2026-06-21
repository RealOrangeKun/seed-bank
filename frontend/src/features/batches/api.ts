import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type {
  BatchDetailOut,
  BatchOut,
  Envelope,
  ImageUrlOut,
  Page,
} from "@/lib/api/types";

const TERMINAL = new Set(["succeeded", "failed", "partial"]);

export interface BatchListParams {
  page: number;
  pageSize: number;
  supplierId?: string;
  countryCode?: string;
}

async function listBatches(params: BatchListParams): Promise<Page<BatchOut>> {
  const result = await api.GET("/api/v1/batches", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
        supplier_id: params.supplierId || undefined,
        country_code: params.countryCode || undefined,
      },
    },
  });
  return unwrap<Page<BatchOut>>(result);
}

async function getBatch(batchId: string): Promise<BatchDetailOut> {
  const result = await api.GET("/api/v1/batches/{batch_id}", {
    params: { path: { batch_id: batchId } },
  });
  const env = await unwrap<Envelope<BatchDetailOut>>(result);
  return env.data;
}

async function getImageUrls(batchId: string): Promise<ImageUrlOut[]> {
  const result = await api.GET("/api/v1/batches/{batch_id}/image-urls", {
    params: { path: { batch_id: batchId } },
  });
  const env = await unwrap<Envelope<ImageUrlOut[]>>(result);
  return env.data;
}

export const batchKeys = {
  all: ["batches"] as const,
  list: (params: BatchListParams) => ["batches", "list", params] as const,
  detail: (id: string) => ["batches", "detail", id] as const,
  imageUrls: (id: string) => ["batches", "image-urls", id] as const,
};

export function useBatches(params: BatchListParams) {
  return useQuery({
    queryKey: batchKeys.list(params),
    queryFn: () => listBatches(params),
    placeholderData: (prev) => prev,
  });
}

/** Batch detail. Polls every 2s until the batch reaches a terminal status. */
export function useBatch(batchId: string) {
  return useQuery({
    queryKey: batchKeys.detail(batchId),
    queryFn: () => getBatch(batchId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && TERMINAL.has(status) ? false : 2000;
    },
  });
}

/** Presigned image URLs for a batch (short-lived). */
export function useBatchImageUrls(batchId: string, enabled: boolean) {
  return useQuery({
    queryKey: batchKeys.imageUrls(batchId),
    queryFn: () => getImageUrls(batchId),
    enabled,
    // URLs expire (default 5 min); refetch a little inside that window.
    staleTime: 4 * 60_000,
  });
}
