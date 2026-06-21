import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type {
  Envelope,
  ExperimentDetailOut,
  ExperimentStatus,
  ExperimentSummaryOut,
  Page,
} from "@/lib/api/types";

const TERMINAL = new Set<ExperimentStatus>(["succeeded", "failed"]);

export interface ExperimentCreateInput {
  name: string;
  model_id: string;
  dataset_id: string;
}

export interface ExperimentListParams {
  page: number;
  pageSize: number;
  modelId?: string;
  datasetId?: string;
  status?: ExperimentStatus;
}

async function listExperiments(
  params: ExperimentListParams,
): Promise<Page<ExperimentSummaryOut>> {
  const result = await api.GET("/api/v1/experiments", {
    params: {
      query: {
        page: params.page,
        page_size: params.pageSize,
        model_id: params.modelId || undefined,
        dataset_id: params.datasetId || undefined,
        status: params.status || undefined,
      },
    },
  });
  return unwrap<Page<ExperimentSummaryOut>>(result);
}

async function getExperiment(experimentId: string): Promise<ExperimentDetailOut> {
  const result = await api.GET("/api/v1/experiments/{experiment_id}", {
    params: { path: { experiment_id: experimentId } },
  });
  const env = await unwrap<Envelope<ExperimentDetailOut>>(result);
  return env.data;
}

async function createExperiment(
  body: ExperimentCreateInput,
): Promise<ExperimentSummaryOut> {
  const result = await api.POST("/api/v1/experiments", { body });
  const env = await unwrap<Envelope<ExperimentSummaryOut>>(result);
  return env.data;
}

export const experimentKeys = {
  all: ["experiments"] as const,
  list: (params: ExperimentListParams) =>
    ["experiments", "list", params] as const,
  detail: (id: string) => ["experiments", "detail", id] as const,
};

export function useExperiments(params: ExperimentListParams) {
  return useQuery({
    queryKey: experimentKeys.list(params),
    queryFn: () => listExperiments(params),
    placeholderData: (prev) => prev,
  });
}

/** Experiment detail. Polls every 2s until the run reaches a terminal status. */
export function useExperiment(experimentId: string) {
  return useQuery({
    queryKey: experimentKeys.detail(experimentId),
    queryFn: () => getExperiment(experimentId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && TERMINAL.has(status) ? false : 2000;
    },
  });
}

export function useCreateExperiment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createExperiment,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: experimentKeys.all });
    },
  });
}
