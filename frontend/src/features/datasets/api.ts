import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type {
  DatasetImportOut,
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
 * Import a labelled dataset from a single YOLO `.zip` (images/ + labels/).
 * The archive is PUT straight to MinIO via a presigned URL (bytes never hit
 * the API), then a background worker unpacks it. Returns once dispatch is
 * acknowledged; callers should poll the dataset's `item_count` for progress.
 */
async function importYoloDataset(datasetId: string, zip: File): Promise<DatasetImportOut> {
  const { upload_url, storage_key } = await getDatasetUploadUrl(datasetId, zip);
  const put = await fetch(upload_url, {
    method: "PUT",
    body: zip,
    headers: { "Content-Type": zip.type || "application/zip" },
  });
  if (!put.ok) {
    throw new Error(`Upload failed for ${zip.name} (HTTP ${put.status})`);
  }
  const result = await api.POST("/api/v1/datasets/{dataset_id}/import", {
    params: { path: { dataset_id: datasetId } },
    body: { zip_storage_key: storage_key },
  });
  const env = await unwrap<Envelope<DatasetImportOut>>(result);
  return env.data;
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

export function useImportYoloDataset(datasetId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (zip: File) => importYoloDataset(datasetId, zip),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: datasetKeys.all });
    },
  });
}
