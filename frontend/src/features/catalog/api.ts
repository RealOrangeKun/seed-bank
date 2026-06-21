import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { Envelope, SeedTypeOut, SupplierOut } from "@/lib/api/types";

// Reference data (seed types, suppliers) the UI renders as dropdowns so users
// never paste a UUID. Both lists are small and change rarely, so they're cached
// aggressively; mutating a supplier invalidates the list.

export interface CreateSupplierInput {
  name: string;
  isGlobal?: boolean;
}

async function listSeedTypes(): Promise<SeedTypeOut[]> {
  const result = await api.GET("/api/v1/seed-types", {});
  const env = await unwrap<Envelope<SeedTypeOut[]>>(result);
  return env.data;
}

async function listSuppliers(): Promise<SupplierOut[]> {
  const result = await api.GET("/api/v1/suppliers", {});
  const env = await unwrap<Envelope<SupplierOut[]>>(result);
  return env.data;
}

async function createSupplier(input: CreateSupplierInput): Promise<SupplierOut> {
  const result = await api.POST("/api/v1/suppliers", {
    body: { name: input.name, is_global: input.isGlobal ?? false },
  });
  const env = await unwrap<Envelope<SupplierOut>>(result);
  return env.data;
}

export const catalogKeys = {
  seedTypes: ["catalog", "seed-types"] as const,
  suppliers: ["catalog", "suppliers"] as const,
};

const REFERENCE_DATA_STALE_MS = 5 * 60 * 1000;

export function useSeedTypes() {
  return useQuery({
    queryKey: catalogKeys.seedTypes,
    queryFn: listSeedTypes,
    staleTime: REFERENCE_DATA_STALE_MS,
  });
}

export function useSuppliers() {
  return useQuery({
    queryKey: catalogKeys.suppliers,
    queryFn: listSuppliers,
    staleTime: REFERENCE_DATA_STALE_MS,
  });
}

export function useCreateSupplier() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateSupplierInput) => createSupplier(input),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: catalogKeys.suppliers });
    },
  });
}
