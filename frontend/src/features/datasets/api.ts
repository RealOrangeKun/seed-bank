import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type {
  DatasetItemOut,
  DatasetOut,
  DatasetUploadUrlOut,
  Envelope,
  Page,
} from "@/lib/api/types";

export interface DatasetListParams {
  page: number;
  pageSize: number;
}

export interface DatasetItemsParams {
  page: number;
  pageSize: number;
}

export interface CreateDatasetInput {
  name: string;
  description?: string | null;
}

export interface DatasetItemsAddedOut {
  added: number;
}

async function listDatasets(params: DatasetListParams): Promise<Page<DatasetOut>> {
  const result = await api.GET("/api/v1/datasets", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
      },
    },
  });
  return unwrap<Page<DatasetOut>>(result);
}

async function getDataset(datasetId: string): Promise<DatasetOut> {
  const result = await api.GET("/api/v1/datasets/{dataset_id}", {
    params: { path: { dataset_id: datasetId } },
  });
  const env = await unwrap<Envelope<DatasetOut>>(result);
  return env.data;
}

async function listDatasetItems(
  datasetId: string,
  params: DatasetItemsParams,
): Promise<Page<DatasetItemOut>> {
  const result = await api.GET("/api/v1/datasets/{dataset_id}/items", {
    params: {
      path: { dataset_id: datasetId },
      query: {
        page: params.page,
        page_size: params.pageSize,
      },
    },
  });
  return unwrap<Page<DatasetItemOut>>(result);
}

async function createDataset(input: CreateDatasetInput): Promise<DatasetOut> {
  const result = await api.POST("/api/v1/datasets", {
    body: {
      name: input.name,
      description: input.description ?? null,
    },
  });
  const env = await unwrap<Envelope<DatasetOut>>(result);
  return env.data;
}

async function addDatasetItems(
  datasetId: string,
  storageKeys: string[],
): Promise<DatasetItemsAddedOut> {
  const result = await api.POST("/api/v1/datasets/{dataset_id}/items", {
    params: { path: { dataset_id: datasetId } },
    body: {
      items: storageKeys.map((image_storage_key) => ({ image_storage_key })),
    },
  });
  const env = await unwrap<Envelope<DatasetItemsAddedOut>>(result);
  return env.data;
}

async function getDatasetUploadUrl(
  datasetId: string,
  file: File,
): Promise<DatasetUploadUrlOut> {
  const result = await api.POST("/api/v1/datasets/{dataset_id}/upload-url", {
    params: { path: { dataset_id: datasetId } },
    body: {
      filename: file.name,
      content_type: file.type || "application/octet-stream",
    },
  });
  const env = await unwrap<Envelope<DatasetUploadUrlOut>>(result);
  return env.data;
}

/**
 * Upload images to a dataset humanely: for each file, mint a presigned PUT URL,
 * PUT the bytes straight to MinIO (bypassing the API), then register all keys
 * via the existing bulk-add endpoint. `onProgress(done, total)` fires after
 * each successful upload so the dialog can show progress.
 */
async function uploadDatasetImages(
  datasetId: string,
  files: File[],
  onProgress?: (done: number, total: number) => void,
): Promise<DatasetItemsAddedOut> {
  const keys: string[] = [];
  for (const [i, file] of files.entries()) {
    const { upload_url, storage_key } = await getDatasetUploadUrl(datasetId, file);
    // Raw PUT to the presigned URL — not through the openapi client (the bytes
    // go directly to object storage, never the API process).
    const put = await fetch(upload_url, {
      method: "PUT",
      body: file,
      headers: { "Content-Type": file.type || "application/octet-stream" },
    });
    if (!put.ok) {
      throw new Error(`Upload failed for ${file.name} (HTTP ${put.status})`);
    }
    keys.push(storage_key);
    onProgress?.(i + 1, files.length);
  }
  return addDatasetItems(datasetId, keys);
}

export const datasetKeys = {
  all: ["datasets"] as const,
  list: (params: DatasetListParams) => ["datasets", "list", params] as const,
  detail: (id: string) => ["datasets", "detail", id] as const,
  items: (id: string, params: DatasetItemsParams) =>
    ["datasets", "items", id, params] as const,
};

export function useDatasets(params: DatasetListParams) {
  return useQuery({
    queryKey: datasetKeys.list(params),
    queryFn: () => listDatasets(params),
    placeholderData: (prev) => prev,
  });
}

export function useDataset(datasetId: string) {
  return useQuery({
    queryKey: datasetKeys.detail(datasetId),
    queryFn: () => getDataset(datasetId),
    enabled: Boolean(datasetId),
  });
}

export function useDatasetItems(datasetId: string, params: DatasetItemsParams) {
  return useQuery({
    queryKey: datasetKeys.items(datasetId, params),
    queryFn: () => listDatasetItems(datasetId, params),
    enabled: Boolean(datasetId),
    placeholderData: (prev) => prev,
  });
}

export function useCreateDataset() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateDatasetInput) => createDataset(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: datasetKeys.all });
    },
  });
}

export function useAddDatasetItems(datasetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (storageKeys: string[]) => addDatasetItems(datasetId, storageKeys),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: datasetKeys.all });
    },
  });
}

export function useUploadDatasetImages(datasetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (vars: {
      files: File[];
      onProgress?: (done: number, total: number) => void;
    }) => uploadDatasetImages(datasetId, vars.files, vars.onProgress),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: datasetKeys.all });
    },
  });
}
