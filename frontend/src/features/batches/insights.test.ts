import { describe, expect, it } from "vitest";

import type { BatchDetailOut, SeedDetectionOut } from "@/lib/api/types";

import { computeInsights, flattenDetections } from "./insights";

function det(overrides: Partial<SeedDetectionOut>): SeedDetectionOut {
  return {
    id: crypto.randomUUID(),
    seed_type_id: null,
    quality: null,
    confidence: "0.5000",
    detection_confidence: null,
    box_x_norm: "0.100000",
    box_y_norm: "0.100000",
    box_w_norm: "0.100000",
    box_h_norm: "0.100000",
    area_px: null,
    width_px: null,
    height_px: null,
    aspect_ratio: null,
    ...overrides,
  } as SeedDetectionOut;
}

/** Wrap a flat detection list into the nested batch graph the API returns. */
function batchWith(detections: SeedDetectionOut[]): BatchDetailOut {
  return {
    images: [
      {
        id: crypto.randomUUID(),
        inferences: [{ id: crypto.randomUUID(), detections }],
      },
    ],
  } as unknown as BatchDetailOut;
}

describe("flattenDetections", () => {
  it("flattens across images and inferences", () => {
    const batch = {
      images: [
        { inferences: [{ detections: [det({}), det({})] }] },
        { inferences: [{ detections: [det({})] }, { detections: [] }] },
      ],
    } as unknown as BatchDetailOut;
    expect(flattenDetections(batch)).toHaveLength(3);
  });

  it("tolerates missing images/inferences/detections", () => {
    expect(flattenDetections({} as BatchDetailOut)).toEqual([]);
  });
});

describe("computeInsights", () => {
  it("counts good/bad/unclassified and computes goodRate over classified only", () => {
    const batch = batchWith([
      det({ quality: "good" }),
      det({ quality: "good" }),
      det({ quality: "bad" }),
      det({ quality: null }), // unclassified — excluded from goodRate denom
    ]);
    const i = computeInsights(batch);
    expect(i.total).toBe(4);
    expect(i.good).toBe(2);
    expect(i.bad).toBe(1);
    expect(i.unclassified).toBe(1);
    // 2 good / 3 classified
    expect(i.goodRate).toBeCloseTo(2 / 3, 5);
  });

  it("returns zeroed insights for an empty batch", () => {
    const i = computeInsights(batchWith([]));
    expect(i.total).toBe(0);
    expect(i.goodRate).toBe(0);
    expect(i.meanConfidence).toBe(0);
    expect(i.confidenceBins).toHaveLength(10);
    expect(i.confidenceBins.every((b) => b.count === 0)).toBe(true);
  });

  it("buckets confidence into ten 10%-wide bins, 1.0 in the last bin", () => {
    const batch = batchWith([
      det({ confidence: "0.0500" }), // bin 0
      det({ confidence: "0.9500" }), // bin 9
      det({ confidence: "1.0000" }), // clamps into bin 9, not out of range
    ]);
    const i = computeInsights(batch);
    expect(i.confidenceBins[0]?.count).toBe(1);
    expect(i.confidenceBins[9]?.count).toBe(2);
  });

  it("averages confidence across all detections", () => {
    const batch = batchWith([
      det({ confidence: "0.2000" }),
      det({ confidence: "0.8000" }),
    ]);
    expect(computeInsights(batch).meanConfidence).toBeCloseTo(0.5, 5);
  });

  it("breaks down by seed type, sorted by total desc", () => {
    const coffee = crypto.randomUUID();
    const maize = crypto.randomUUID();
    const batch = batchWith([
      det({ seed_type_id: coffee, quality: "good" }),
      det({ seed_type_id: coffee, quality: "bad" }),
      det({ seed_type_id: coffee, quality: "good" }),
      det({ seed_type_id: maize, quality: "good" }),
    ]);
    const i = computeInsights(batch);
    expect(i.bySeedType[0]?.seedTypeId).toBe(coffee);
    expect(i.bySeedType[0]?.total).toBe(3);
    expect(i.bySeedType[0]?.good).toBe(2);
    expect(i.bySeedType[1]?.seedTypeId).toBe(maize);
  });
});
