import { apiData } from "./client";
import type {
  BatchDetailOut,
  BatchOut,
  CapturedPhoto,
  Page,
} from "./types";

/**
 * Upload captured photos for analysis. React Native's `FormData` accepts a
 * `{ uri, name, type }` part for a local file; the runtime streams the file and
 * sets the multipart boundary itself.
 */
export async function analyzePhotos(photos: CapturedPhoto[]): Promise<BatchOut> {
  const form = new FormData();
  photos.forEach((photo, i) => {
    form.append("files", {
      uri: photo.uri,
      name: `seed-${i + 1}.jpg`,
      type: "image/jpeg",
    } as unknown as Blob);
  });
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
