import { Platform } from "react-native";

import { apiData } from "./client";
import type {
  BatchDetailOut,
  BatchOut,
  CapturedPhoto,
  Page,
} from "./types";

/**
 * Build the multipart part for one captured photo.
 *
 * Native (iOS/Android) `FormData` accepts a `{ uri, name, type }` descriptor and
 * streams the local file itself. On web there is no such affordance — appending
 * that object stringifies it to `"[object Object]"`, which the backend rejects
 * with HTTP 422 ("files" must be a file, not a string). So on web we resolve the
 * capture URI (a `blob:`/`data:` URL) into a real `Blob` and append a `File`.
 */
async function toUploadPart(photo: CapturedPhoto, index: number): Promise<Blob> {
  const name = `seed-${index + 1}.jpg`;
  if (Platform.OS === "web") {
    const res = await fetch(photo.uri);
    const blob = await res.blob();
    return new File([blob], name, { type: blob.type || "image/jpeg" });
  }
  return { uri: photo.uri, name, type: "image/jpeg" } as unknown as Blob;
}

/**
 * Upload captured photos for analysis as `multipart/form-data` (field `files`).
 * The runtime sets the multipart boundary itself.
 */
export async function analyzePhotos(photos: CapturedPhoto[]): Promise<BatchOut> {
  const form = new FormData();
  const parts = await Promise.all(photos.map(toUploadPart));
  parts.forEach((part) => form.append("files", part));
  return apiData<BatchOut>("/api/v1/analyze", { method: "POST", form });
}

export async function listBatches(page = 1, pageSize = 20): Promise<Page<BatchOut>> {
  return apiData<Page<BatchOut>>(
    `/api/v1/batches?page=${page}&page_size=${pageSize}`,
  );
}

export async function getBatch(id: string): Promise<BatchDetailOut> {
  return apiData<BatchDetailOut>(`/api/v1/batches/${id}`);
}

export interface BatchTally {
  total: number;
  good: number;
  bad: number;
  goodRate: number;
  meanConfidence: number;
}

/** Flatten + tally detections across a batch's image → inference → detection graph. */
export function tallyBatch(batch: BatchDetailOut): BatchTally {
  const dets = (batch.images ?? []).flatMap((img) =>
    (img.inferences ?? []).flatMap((inf) => inf.detections ?? []),
  );
  const good = dets.filter((d) => d.quality === "good").length;
  const bad = dets.filter((d) => d.quality === "bad").length;
  const classified = good + bad;
  const meanConfidence = dets.length
    ? dets.reduce((sum, d) => sum + Number(d.confidence), 0) / dets.length
    : 0;
  return {
    total: dets.length,
    good,
    bad,
    goodRate: classified ? good / classified : 0,
    meanConfidence,
  };
}

const TERMINAL: ReadonlySet<string> = new Set(["succeeded", "failed", "partial"]);
export const isTerminal = (status: string): boolean => TERMINAL.has(status);
