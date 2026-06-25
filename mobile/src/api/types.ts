/** Minimal API shapes used by the mobile app (subset of the backend contract). */

export type BatchStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "partial";

export type SeedQuality = "good" | "bad" | null;

export interface TokenPair {
  access_token: string;
  refresh_token: string;
}

export interface MeOut {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
}

export interface BatchOut {
  id: string;
  status: BatchStatus;
  image_count: number;
  submitted_at: string;
  duration_ms: number | null;
}

export interface SeedDetectionOut {
  id: string;
  quality: SeedQuality;
  confidence: string | number;
}

export interface InferenceOut {
  id: string;
  detections: SeedDetectionOut[] | null;
}

export interface ScanImageOut {
  id: string;
  inferences: InferenceOut[] | null;
}

export interface BatchDetailOut extends BatchOut {
  images: ScanImageOut[] | null;
  error_message?: string | null;
}

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

/** A photo captured by the camera, ready for multipart upload. */
export interface CapturedPhoto {
  uri: string;
  width: number;
  height: number;
}
