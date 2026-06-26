/**
 * Ergonomic aliases over the generated OpenAPI schema. Components reference
 * these instead of digging into `components["schemas"][...]`. If the backend
 * contract changes, `npm run gen:api` regenerates `schema.d.ts` and the
 * compiler flags every break here.
 */
import type { components } from "./schema";

type S = components["schemas"];

// ── Enums (string unions) ────────────────────────────────────────────────────
export type Role = S["Role"];
export type BatchStatus = S["BatchStatus"];
export type BatchSource = S["BatchSource"];
export type ModelKind = S["ModelKind"];
export type ModelBackend = S["ModelBackend"];
export type ModelStatus = S["ModelStatus"];
export type ExperimentStatus = S["ExperimentStatus"];
export type SeedQuality = S["SeedQuality"];
export type LocationSource = S["LocationSource"];

// ── Auth / users ─────────────────────────────────────────────────────────────
export type MeOut = S["MeOut"];
export type UserListOut = S["UserListOut"];
export type TokenPair = S["TokenPair"];
export type ApiKeyOut = S["ApiKeyOut"];

// ── Analyze / batches ────────────────────────────────────────────────────────
export type BatchOut = S["BatchOut"];
export type BatchDetailOut = S["BatchDetailOut"];
export type ScanImageOut = S["ScanImageOut"];
export type InferenceOut = S["InferenceOut"];
export type SeedDetectionOut = S["SeedDetectionOut"];
export type ImageUrlOut = S["ImageUrlOut"];

// ── ML platform ──────────────────────────────────────────────────────────────
export type ModelOut = S["ModelOut"];
export type ModelPerformanceOut = S["ModelPerformanceOut"];
export type OfflineMetricOut = S["OfflineMetricOut"];
export type DatasetOut = S["DatasetOut"];
export type DatasetItemOut = S["DatasetItemOut"];
export type ExperimentSummaryOut = S["ExperimentSummaryOut"];
export type ExperimentDetailOut = S["ExperimentDetailOut"];
export type TrafficSplitOut = S["TrafficSplitOut"];

// ── Catalog (reference data) ──────────────────────────────────────────────────
export type SeedTypeOut = S["SeedTypeOut"];
export type SupplierOut = S["SupplierOut"];

// ── Shared response envelopes (generic; defined here to avoid the bracketed
//    generic names openapi-typescript emits) ─────────────────────────────────
export interface Envelope<T> {
  data: T;
}

export interface PageMeta {
  page: number;
  page_size: number;
  total: number;
  has_more: boolean;
}

export interface Page<T> {
  data: T[];
  meta: PageMeta;
}

// ── Enum value lists (for selects / iteration; kept in sync with the unions
//    above — the `satisfies` clause makes drift a compile error) ──────────────
export const ROLES = ["end_user", "ai_developer", "admin"] as const satisfies Role[];
export const MODEL_KINDS = [
  "detection",
  "classification",
] as const satisfies ModelKind[];
export const MODEL_BACKENDS = [
  "torch_local",
  "roboflow",
  "yolo",
] as const satisfies ModelBackend[];
export const MODEL_STATUSES = [
  "registered",
  "staging",
  "production",
  "archived",
] as const satisfies ModelStatus[];
// Allowed forward transitions — mirrors `_TRANSITIONS` in
// services/model_registry_service.py. `archived` is a terminal sink.
export const MODEL_STATUS_TRANSITIONS = {
  registered: ["staging", "archived"],
  staging: ["production", "archived"],
  production: ["archived"],
  archived: [],
} as const satisfies Record<ModelStatus, ModelStatus[]>;
export const BATCH_STATUSES = [
  "pending",
  "running",
  "succeeded",
  "failed",
  "partial",
] as const satisfies BatchStatus[];
export const EXPERIMENT_STATUSES = [
  "pending",
  "running",
  "succeeded",
  "failed",
] as const satisfies ExperimentStatus[];
