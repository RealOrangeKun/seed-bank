import { useMutation } from "@tanstack/react-query";

import { api, unwrap } from "@/lib/api/client";
import type { BatchOut, Envelope } from "@/lib/api/types";

export interface AnalyzeInput {
  files: File[];
  supplierId?: string;
  seedTypeId?: string;
  modelId?: string;
  countryCode?: string;
  gpsLat?: string;
  gpsLong?: string;
}

async function analyze(input: AnalyzeInput): Promise<BatchOut> {
  const form = new FormData();
  for (const file of input.files) form.append("files", file);
  if (input.supplierId) form.append("supplier_id", input.supplierId);
  if (input.seedTypeId) form.append("seed_type_id", input.seedTypeId);
  if (input.modelId) form.append("model_id", input.modelId);
  if (input.countryCode) form.append("country_code", input.countryCode);
  if (input.gpsLat) form.append("gps_lat", input.gpsLat);
  if (input.gpsLong) form.append("gps_long", input.gpsLong);

  // Multipart: hand the client the FormData verbatim (bodySerializer bypasses
  // JSON encoding; openapi-fetch drops Content-Type so the browser sets the
  // multipart boundary). Still flows through auth + refresh middleware.
  const result = await api.POST("/api/v1/analyze", {
    body: form as unknown as never,
    bodySerializer: (body) => body as unknown as FormData,
  });
  const env = await unwrap<Envelope<BatchOut>>(result);
  return env.data;
}

export function useAnalyze() {
  return useMutation({ mutationFn: analyze });
}
