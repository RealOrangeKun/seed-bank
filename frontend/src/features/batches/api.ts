import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import { tokenStore } from "@/lib/auth/token-store";
import { env } from "@/lib/env";
import type {
  BatchDetailOut,
  BatchOut,
  Envelope,
  ImageUrlOut,
  Page,
} from "@/lib/api/types";
import type { components } from "@/lib/api/schema";

export type ShareLinkOut = components["schemas"]["ShareLinkOut"];
export type SharedBatchOut = components["schemas"]["SharedBatchOut"];

const TERMINAL = new Set(["succeeded", "failed", "partial"]);

export interface BatchListParams {
  page: number;
  pageSize: number;
  supplierId?: string;
  countryCode?: string;
  /** Scope to a client origin ("web"/"mobile"). The web app passes "web" so its
   *  history shows only web scans, never mobile or realtime frames. */
  source?: "web" | "mobile" | "api" | "sdk";
}

async function listBatches(params: BatchListParams): Promise<Page<BatchOut>> {
  const result = await api.GET("/api/v1/batches", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
        supplier_id: params.supplierId || undefined,
        country_code: params.countryCode || undefined,
        source: params.source || undefined,
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

// ── Mutations: delete + bulk delete ──────────────────────────────────────────

async function deleteBatch(batchId: string): Promise<void> {
  const result = await api.DELETE("/api/v1/batches/{batch_id}", {
    params: { path: { batch_id: batchId } },
  });
  // 204 No Content — unwrap only to surface a Problem on failure.
  if (result.error !== undefined || !result.response.ok) {
    await unwrap(result);
  }
}

async function bulkDeleteBatches(batchIds: string[]): Promise<number> {
  const result = await api.POST("/api/v1/batches/delete", {
    body: { batch_ids: batchIds },
  });
  const env = await unwrap<Envelope<{ deleted: number }>>(result);
  return env.data.deleted;
}

/** Soft-delete a single batch, then invalidate every batches query. */
export function useDeleteBatch() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteBatch,
    onSuccess: () => qc.invalidateQueries({ queryKey: batchKeys.all }),
  });
}

/** Soft-delete many batches; resolves to the count actually deleted. */
export function useBulkDeleteBatches() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: bulkDeleteBatches,
    onSuccess: () => qc.invalidateQueries({ queryKey: batchKeys.all }),
  });
}

// ── Export: CSV / JSON downloads ─────────────────────────────────────────────

export type ExportFormat = "csv" | "json";

/**
 * Download a batch's detections as a file. These endpoints stream a body with a
 * `Content-Disposition` header, so we bypass the typed JSON client: fetch the
 * blob with the bearer token, then click a synthetic anchor to save it. The
 * filename comes from the response header, falling back to a sensible default.
 */
export async function downloadBatchExport(
  batchId: string,
  format: ExportFormat,
): Promise<void> {
  const token = tokenStore.getAccessToken();
  const res = await fetch(`${env.apiOrigin}/api/v1/batches/${batchId}/export.${format}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) {
    throw new Error(`Export failed (${res.status})`);
  }
  const blob = await res.blob();
  const disposition = res.headers.get("content-disposition") ?? "";
  const match = /filename="?([^"]+)"?/.exec(disposition);
  const filename = match?.[1] ?? `batch-${batchId}.${format}`;

  const objectUrl = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(objectUrl);
}

/** Absolute URL for the server-rendered annotated image (boxes burned in). */
export function annotatedImageUrl(batchId: string, imageId: string): string {
  return `${env.apiOrigin}/api/v1/batches/${batchId}/images/${imageId}/annotated.png`;
}

/**
 * Fetch the annotated PNG with the bearer token (the <img> tag can't send auth
 * headers) and return a blob URL the caller renders + revokes.
 */
export async function fetchAnnotatedImage(
  batchId: string,
  imageId: string,
): Promise<string> {
  const token = tokenStore.getAccessToken();
  const res = await fetch(annotatedImageUrl(batchId, imageId), {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!res.ok) throw new Error(`Annotated image failed (${res.status})`);
  return URL.createObjectURL(await res.blob());
}

// ── Share links ──────────────────────────────────────────────────────────────

async function createShare(batchId: string): Promise<ShareLinkOut> {
  const result = await api.POST("/api/v1/batches/{batch_id}/share", {
    params: { path: { batch_id: batchId } },
  });
  const env_ = await unwrap<Envelope<ShareLinkOut>>(result);
  return env_.data;
}

async function revokeShare(batchId: string): Promise<void> {
  const result = await api.DELETE("/api/v1/batches/{batch_id}/share", {
    params: { path: { batch_id: batchId } },
  });
  if (result.error !== undefined || !result.response.ok) await unwrap(result);
}

export function useCreateShare() {
  return useMutation({ mutationFn: createShare });
}

export function useRevokeShare() {
  return useMutation({ mutationFn: revokeShare });
}

/** Public read-only shared batch (no auth). Used by the /shared/:token page. */
async function getSharedBatch(token: string): Promise<SharedBatchOut> {
  const result = await api.GET("/api/v1/shared/{token}", {
    params: { path: { token } },
  });
  const env_ = await unwrap<Envelope<SharedBatchOut>>(result);
  return env_.data;
}

export function useSharedBatch(token: string) {
  return useQuery({
    queryKey: ["shared", token],
    queryFn: () => getSharedBatch(token),
    retry: false,
  });
}
