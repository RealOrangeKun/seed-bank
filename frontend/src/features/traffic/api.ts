import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { Envelope, ModelKind, TrafficSplitOut } from "@/lib/api/types";

export interface TrafficSegment {
  kind: ModelKind;
  seedTypeId?: string;
}

export interface TrafficEntryInput {
  model_id: string;
  weight: number;
  valid_from?: string | null;
  valid_until?: string | null;
}

export interface ReplaceSplitsInput {
  kind: ModelKind;
  seedTypeId?: string;
  entries: TrafficEntryInput[];
}

async function listSplits(segment: TrafficSegment): Promise<TrafficSplitOut[]> {
  const result = await api.GET("/api/v1/traffic-splits", {
    params: {
      query: {
        kind: segment.kind,
        seed_type_id: segment.seedTypeId || undefined,
      },
    },
  });
  const env = await unwrap<Envelope<TrafficSplitOut[]>>(result);
  return env.data ?? [];
}

async function replaceSplits(input: ReplaceSplitsInput): Promise<TrafficSplitOut[]> {
  const result = await api.PATCH("/api/v1/traffic-splits", {
    body: {
      kind: input.kind,
      seed_type_id: input.seedTypeId || null,
      entries: input.entries,
    },
  });
  const env = await unwrap<Envelope<TrafficSplitOut[]>>(result);
  return env.data ?? [];
}

export const trafficKeys = {
  all: ["traffic-splits"] as const,
  list: (segment: TrafficSegment) =>
    ["traffic-splits", "list", segment.kind, segment.seedTypeId ?? null] as const,
};

/** Current active splits for a (kind, seed_type_id) segment. `enabled` gates the fetch until the user loads a segment. */
export function useTrafficSplits(segment: TrafficSegment, enabled: boolean) {
  return useQuery({
    queryKey: trafficKeys.list(segment),
    queryFn: () => listSplits(segment),
    enabled,
    placeholderData: (prev) => prev,
  });
}

/** Atomically replace all active splits for a segment. */
export function useReplaceTrafficSplits() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: replaceSplits,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: trafficKeys.all });
    },
  });
}
