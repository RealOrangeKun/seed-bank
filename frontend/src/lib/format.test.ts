import { describe, expect, it } from "vitest";

import {
  formatBytes,
  formatConfidence,
  formatDuration,
  humanize,
  shortId,
  toNumber,
} from "./format";

describe("format helpers", () => {
  it("parses API decimal strings without precision loss in display", () => {
    expect(toNumber("0.9234")).toBeCloseTo(0.9234);
    expect(toNumber(null)).toBe(0);
    expect(toNumber(undefined)).toBe(0);
  });

  it("formats confidence as a percentage", () => {
    expect(formatConfidence("0.923")).toBe("92.3%");
    expect(formatConfidence(1)).toBe("100.0%");
    expect(formatConfidence(null)).toBe("0.0%");
  });

  it("formats durations", () => {
    expect(formatDuration(340)).toBe("340ms");
    expect(formatDuration(1200)).toBe("1.2s");
    expect(formatDuration(null)).toBe("—");
  });

  it("formats byte sizes", () => {
    expect(formatBytes(0)).toBe("0 B");
    expect(formatBytes(1024)).toBe("1.0 KB");
    expect(formatBytes(1_500_000)).toBe("1.4 MB");
  });

  it("shortens UUIDs", () => {
    expect(shortId("a1b2c3d4-e5f6-7890-abcd-ef1234567890")).toBe("a1b2c3d4");
    expect(shortId(null)).toBe("—");
  });

  it("humanizes snake_case enums", () => {
    expect(humanize("ai_developer")).toBe("Ai Developer");
    expect(humanize("torch_local")).toBe("Torch Local");
    expect(humanize(null)).toBe("—");
  });
});
