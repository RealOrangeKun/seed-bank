import { useQuery } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { Envelope } from "@/lib/api/types";
import type { components } from "@/lib/api/schema";

export type AnalyticsOut = components["schemas"]["AnalyticsOut"];

async function getAnalytics(windowDays: number): Promise<AnalyticsOut> {
  const result = await api.GET("/api/v1/analytics", {
    params: { query: { window_days: windowDays } },
  });
  const env = await unwrap<Envelope<AnalyticsOut>>(result);
  return env.data;
}

export const analyticsKeys = {
  all: ["analytics"] as const,
  summary: (windowDays: number) => ["analytics", windowDays] as const,
};

export function useAnalytics(windowDays = 30) {
  return useQuery({
    queryKey: analyticsKeys.summary(windowDays),
    queryFn: () => getAnalytics(windowDays),
  });
}
