import { QueryClient } from "@tanstack/react-query";

import { isApiError } from "./api/errors";

/**
 * Shared React Query client. We do not retry 4xx (client errors / auth) — only
 * transient failures are worth retrying, and never an auth/permission error.
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: (failureCount, error) => {
        if (isApiError(error) && error.status < 500) return false;
        return failureCount < 2;
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});
