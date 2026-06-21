import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, unwrap } from "@/lib/api/client";
import { apiErrorFromResponse } from "@/lib/api/errors";
import type { ApiKeyOut, Envelope, Page } from "@/lib/api/types";

export interface ApiKeyListParams {
  page: number;
  pageSize: number;
}

export interface CreateApiKeyInput {
  name: string;
  scopes: string[];
  expiresAt?: string;
}

async function listApiKeys(params: ApiKeyListParams): Promise<Page<ApiKeyOut>> {
  const result = await api.GET("/api/v1/api-keys", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
      },
    },
  });
  return unwrap<Page<ApiKeyOut>>(result);
}

async function createApiKey(input: CreateApiKeyInput): Promise<ApiKeyOut> {
  const result = await api.POST("/api/v1/api-keys", {
    body: {
      name: input.name,
      scopes: input.scopes,
      expires_at: input.expiresAt ?? null,
    },
  });
  const env = await unwrap<Envelope<ApiKeyOut>>(result);
  return env.data;
}

async function revokeApiKey(keyId: string): Promise<void> {
  const result = await api.DELETE("/api/v1/api-keys/{key_id}", {
    params: { path: { key_id: keyId } },
  });
  // 204 No Content: there is no body to unwrap, so check the raw result.
  if (result.error || !result.response.ok) {
    throw await apiErrorFromResponse(result.response);
  }
}

export const apiKeyKeys = {
  all: ["api-keys"] as const,
  list: (params: ApiKeyListParams) => ["api-keys", "list", params] as const,
};

export function useApiKeys(params: ApiKeyListParams) {
  return useQuery({
    queryKey: apiKeyKeys.list(params),
    queryFn: () => listApiKeys(params),
    placeholderData: (prev) => prev,
  });
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createApiKey,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: apiKeyKeys.all });
    },
  });
}

export function useRevokeApiKey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: revokeApiKey,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: apiKeyKeys.all });
      toast.success("API key revoked.");
    },
  });
}
