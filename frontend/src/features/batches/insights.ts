/**
 * Client-side aggregation of a batch's detections into AI result insights.
 *
 * The batch-detail endpoint already returns the full detection graph, so we
 * derive the headline stats (counts, good/bad split, confidence distribution,
 * per-seed-type breakdown) in the browser — no extra round-trip. Confidence
 * arrives as a decimal *string*; everything here normalizes through
 * `toNumber` so the math is float-safe at the edge only.
 */
import { toNumber } from "@/lib/format";
import type { BatchDetailOut, ScanImageOut, SeedDetectionOut } from "@/lib/api/types";

export interface ConfidenceBin {
  /** Lower bound of the bin, e.g. 0.8 for the 80–90% bucket. */
  from: number;
  /** Upper bound (exclusive except the last bin). */
  to: number;
  count: number;
}

export interface SeedTypeBreakdown {
  seedTypeId: string | null;
  good: number;
  bad: number;
  unclassified: number;
  total: number;
}

export interface BatchInsights {
  total: number;
  good: number;
  bad: number;
  unclassified: number;
  /** Good as a fraction of *classified* seeds (good + bad), 0 when none. */
  goodRate: number;
  /** Mean detection/quality confidence across all detections, 0 when none. */
  meanConfidence: number;
  /** Ten 10%-wide confidence bins, 0–100%. */
  confidenceBins: ConfidenceBin[];
  bySeedType: SeedTypeBreakdown[];
}

/** Flatten every detection across a batch's images and inferences. */
export function flattenDetections(batch: BatchDetailOut): SeedDetectionOut[] {
  return (batch.images ?? []).flatMap((img) =>
    (img.inferences ?? []).flatMap((inf) => inf.detections ?? []),
  );
}

function emptyBins(): ConfidenceBin[] {
  return Array.from({ length: 10 }, (_, i) => ({
    from: i / 10,
    to: (i + 1) / 10,
    count: 0,
  }));
}

/** Compute headline insights for a batch from its detection graph. */
export function computeInsights(batch: BatchDetailOut): BatchInsights {
  const detections = flattenDetections(batch);
  const total = detections.length;

  let good = 0;
  let bad = 0;
  let unclassified = 0;
  let confidenceSum = 0;
  const bins = emptyBins();
  const byType = new Map<string | null, SeedTypeBreakdown>();

  for (const d of detections) {
    const conf = toNumber(d.confidence);
    confidenceSum += conf;
    // Clamp into [0, 9] so a confidence of exactly 1.0 lands in the last bin.
    const idx = Math.min(9, Math.max(0, Math.floor(conf * 10)));
    const bin = bins[idx];
    if (bin) bin.count += 1;

    const typeId = d.seed_type_id ?? null;
    const row = byType.get(typeId) ?? {
      seedTypeId: typeId,
      good: 0,
      bad: 0,
      unclassified: 0,
      total: 0,
    };

    if (d.quality === "good") {
      good += 1;
      row.good += 1;
    } else if (d.quality === "bad") {
      bad += 1;
      row.bad += 1;
    } else {
      unclassified += 1;
      row.unclassified += 1;
    }
    row.total += 1;
    byType.set(typeId, row);
  }

  const classified = good + bad;
  return {
    total,
    good,
    bad,
    unclassified,
    goodRate: classified > 0 ? good / classified : 0,
    meanConfidence: total > 0 ? confidenceSum / total : 0,
    confidenceBins: bins,
    bySeedType: [...byType.values()].sort((a, b) => b.total - a.total),
  };
}

/** Good/bad verdict for a single image (or null when nothing was classified). */
export type ImageVerdict = "good" | "bad" | null;

export interface ImageInsights {
  total: number;
  good: number;
  bad: number;
  unclassified: number;
  /** Good as a fraction of *classified* seeds (good + bad); null when none. */
  goodRate: number | null;
}

/** Tally one image's detections into good/bad/unclassified counts + good-rate. */
export function computeImageInsights(image: ScanImageOut): ImageInsights {
  const dets = (image.inferences ?? []).flatMap((inf) => inf.detections ?? []);
  let good = 0;
  let bad = 0;
  let unclassified = 0;
  for (const d of dets) {
    if (d.quality === "good") good += 1;
    else if (d.quality === "bad") bad += 1;
    else unclassified += 1;
  }
  const classified = good + bad;
  return {
    total: dets.length,
    good,
    bad,
    unclassified,
    goodRate: classified > 0 ? good / classified : null,
  };
}

/**
 * Classify an image as a good/bad batch from its good-seed share and the
 * configured threshold. Returns null when no seed was classified (the verdict
 * is undefined, not "bad").
 */
export function verdictFor(goodRate: number | null, threshold: number): ImageVerdict {
  if (goodRate === null) return null;
  return goodRate >= threshold ? "good" : "bad";
}
