import { Platform } from "react-native";

import { apiData, apiFetch } from "./client";
import type {
  BatchDetailOut,
  BatchOut,
  CapturedPhoto,
  Page,
} from "./types";

/**
 * Append one photo as a multipart "files" part.
 *
 * Native and web need different shapes for the same field:
 * - React Native's `FormData` accepts a `{ uri, name, type }` object and streams
 *   the local file itself.
 * - Browser `FormData` does NOT — that object would serialize to
 *   "[object Object]" and the server rejects the upload (HTTP 422). On web the
 *   camera/library `uri` is a `blob:`/`data:` URL we can fetch back into a real
 *   `Blob` and append as a file.
 */
async function appendPhoto(form: FormData, photo: CapturedPhoto, index: number): Promise<void> {
  const name = `seed-${index + 1}.jpg`;
  if (Platform.OS === "web") {
    const res = await fetch(photo.uri);
    const blob = await res.blob();
    form.append("files", blob, name);
  } else {
    form.append("files", {
      uri: photo.uri,
      name,
      type: "image/jpeg",
    } as unknown as Blob);
  }
}

/**
 * Upload captured photos for analysis.
 *
 * ``source`` tags the scan's origin so history stays split per app: "mobile"
 * shows up in the mobile history; "mobile_realtime" (live-video frames) is
 * hidden from history entirely so a realtime session doesn't bury real scans.
 */
export async function analyzePhotos(
  photos: CapturedPhoto[],
  source: "mobile" | "mobile_realtime" = "mobile",
): Promise<BatchOut> {
  const form = new FormData();
  for (let i = 0; i < photos.length; i += 1) {
    await appendPhoto(form, photos[i], i);
  }
  // Phones always run the fast YOLO one-shot pipeline — we value quick scanning
  // over the slower two-stage accuracy on mobile.
  form.append("mode", "fast");
  form.append("source", source);
  return apiData<BatchOut>("/api/v1/analyze", { method: "POST", form });
}

/** Submit a single live frame for analysis (realtime mode). Tagged so the
 *  per-frame batches stay out of history. */
export async function analyzeFrame(frame: CapturedPhoto): Promise<BatchOut> {
  return analyzePhotos([frame], "mobile_realtime");
}

/**
 * Poll a batch until it reaches a terminal status (or times out). Used by the
 * realtime screen to await each frame's result before grabbing the next one.
 * Aborting via `signal` throws an `AbortError` so the caller's loop can exit.
 */
export async function waitForBatch(
  id: string,
  opts: { intervalMs?: number; timeoutMs?: number; signal?: AbortSignal } = {},
): Promise<BatchDetailOut> {
  const { intervalMs = 700, timeoutMs = 20000, signal } = opts;
  const start = Date.now();
  for (;;) {
    if (signal?.aborted) {
      const err = new Error("aborted");
      err.name = "AbortError";
      throw err;
    }
    const batch = await getBatch(id);
    if (isTerminal(batch.status) || Date.now() - start > timeoutMs) return batch;
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
}

export async function listBatches(page = 1, pageSize = 20): Promise<Page<BatchOut>> {
  // Show the user's full scan history regardless of origin (api/web/mobile).
  // No `source` filter, so the server returns every batch the user owns except
  // the realtime live-frame batches, which it hides from history by default.
  //
  // Use `apiFetch`, not `apiData`: the paginated response is `{ data, meta }`,
  // which already *is* the `Page` — `apiData` would strip it to the inner array
  // and drop `meta`, leaving the history screen with no `.data` to read.
  return apiFetch<Page<BatchOut>>(
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
