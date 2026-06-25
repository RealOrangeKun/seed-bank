import { useMutation } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { Envelope } from "@/lib/api/types";
import type { components } from "@/lib/api/schema";

export type BatchCompareOut = components["schemas"]["BatchCompareOut"];
export type BatchCompareRow = components["schemas"]["BatchCompareRow"];

async function compareBatches(batchIds: string[]): Promise<BatchCompareOut> {
  const result = await api.POST("/api/v1/batches/compare", {
    body: { batch_ids: batchIds },
  });
  const env = await unwrap<Envelope<BatchCompareOut>>(result);
  return env.data;
}

export function useCompareBatches() {
  return useMutation({ mutationFn: compareBatches });
}
