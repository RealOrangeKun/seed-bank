import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type {
  Envelope,
  ModelBackend,
  ModelKind,
  ModelOut,
  ModelPerformanceOut,
  ModelStatus,
  Page,
} from "@/lib/api/types";

export interface ModelListParams {
  page: number;
  pageSize: number;
  kind?: ModelKind;
  status?: ModelStatus;
  seedTypeId?: string;
}

export interface ModelRegisterInput {
  name: string;
  version: string;
  kind: ModelKind;
  backend: ModelBackend;
  artifactUri: string;
  seedTypeId?: string;
}

async function listModels(params: ModelListParams): Promise<Page<ModelOut>> {
  const result = await api.GET("/api/v1/models", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
        kind: params.kind ?? undefined,
        status: params.status ?? undefined,
        seed_type_id: params.seedTypeId || undefined,
      },
    },
  });
  return unwrap<Page<ModelOut>>(result);
}

async function getModel(modelId: string): Promise<ModelOut> {
  const result = await api.GET("/api/v1/models/{model_id}", {
    params: { path: { model_id: modelId } },
  });
  const env = await unwrap<Envelope<ModelOut>>(result);
  return env.data;
}

async function getModelPerformance(modelId: string): Promise<ModelPerformanceOut> {
  const result = await api.GET("/api/v1/models/{model_id}/performance", {
    params: { path: { model_id: modelId } },
  });
  const env = await unwrap<Envelope<ModelPerformanceOut>>(result);
  return env.data;
}

async function registerModel(input: ModelRegisterInput): Promise<ModelOut> {
  const result = await api.POST("/api/v1/models", {
    body: {
      name: input.name,
      version: input.version,
      kind: input.kind,
      backend: input.backend,
      artifact_uri: input.artifactUri,
      seed_type_id: input.seedTypeId || null,
    },
  });
  const env = await unwrap<Envelope<ModelOut>>(result);
  return env.data;
}

async function updateModelStatus(
  modelId: string,
  status: ModelStatus,
): Promise<ModelOut> {
  const result = await api.PATCH("/api/v1/models/{model_id}", {
    params: { path: { model_id: modelId } },
    body: { status },
  });
  const env = await unwrap<Envelope<ModelOut>>(result);
  return env.data;
}

export const modelKeys = {
  all: ["models"] as const,
  list: (params: ModelListParams) => ["models", "list", params] as const,
  detail: (id: string) => ["models", "detail", id] as const,
  performance: (id: string) => ["models", "performance", id] as const,
};

export function useModels(params: ModelListParams, options?: { enabled?: boolean }) {
  return useQuery({
    queryKey: modelKeys.list(params),
    queryFn: () => listModels(params),
    placeholderData: (prev) => prev,
    // `GET /models` is gated to ai_developer/admin; callers on an end-user
    // surface pass `enabled: false` so the query never fires a 403.
    enabled: options?.enabled ?? true,
  });
}

export function useModel(modelId: string) {
  return useQuery({
    queryKey: modelKeys.detail(modelId),
    queryFn: () => getModel(modelId),
    enabled: Boolean(modelId),
  });
}

export function useModelPerformance(modelId: string) {
  return useQuery({
    queryKey: modelKeys.performance(modelId),
    queryFn: () => getModelPerformance(modelId),
    enabled: Boolean(modelId),
  });
}

export function useRegisterModel() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: ModelRegisterInput) => registerModel(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelKeys.all });
    },
  });
}

export function useUpdateModelStatus(modelId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (status: ModelStatus) => updateModelStatus(modelId, status),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: modelKeys.all });
    },
  });
}
