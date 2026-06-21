import { describe, expect, it } from "vitest";

import type { BatchOut } from "@/lib/api/types";

import { computeStats } from "./stats-strip";

function batch(overrides: Partial<BatchOut>): BatchOut {
  return {
    id: crypto.randomUUID(),
    user_id: crypto.randomUUID(),
    status: "succeeded",
    source: "api",
    submitted_at: new Date().toISOString(),
    image_count: 1,
    ...overrides,
  } as BatchOut;
}

describe("computeStats", () => {
  it("totals scans and images", () => {
    const s = computeStats([batch({ image_count: 2 }), batch({ image_count: 3 })]);
    expect(s.totalScans).toBe(2);
    expect(s.totalImages).toBe(5);
  });

  it("counts succeeded + partial toward success rate", () => {
    const s = computeStats([
      batch({ status: "succeeded" }),
      batch({ status: "partial" }),
      batch({ status: "failed" }),
      batch({ status: "running" }),
    ]);
    expect(s.succeeded).toBe(2);
    expect(s.successRate).toBeCloseTo(0.5, 5);
  });

  it("returns zeroed stats with a 14-slot activity array for no batches", () => {
    const s = computeStats([]);
    expect(s.totalScans).toBe(0);
    expect(s.successRate).toBe(0);
    expect(s.activity).toHaveLength(14);
    expect(s.activity.every((v) => v === 0)).toBe(true);
  });

  it("buckets recent activity by day, newest in the last slot", () => {
    const now = Date.now();
    const today = new Date(now).toISOString();
    const threeDaysAgo = new Date(now - 3 * 86_400_000).toISOString();
    const s = computeStats([
      batch({ submitted_at: today }),
      batch({ submitted_at: today }),
      batch({ submitted_at: threeDaysAgo }),
    ]);
    // Last slot = today (2), slot 3-from-end = three days ago (1).
    expect(s.activity[13]).toBe(2);
    expect(s.activity[10]).toBe(1);
  });

  it("ignores batches older than the window", () => {
    const old = new Date(Date.now() - 30 * 86_400_000).toISOString();
    const s = computeStats([batch({ submitted_at: old })]);
    expect(s.totalScans).toBe(1); // still counted in totals
    expect(s.activity.every((v) => v === 0)).toBe(true); // but not in sparkline
  });
});
