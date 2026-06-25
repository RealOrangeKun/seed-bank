import { describe, expect, it } from "vitest";

import { ar, arPlurals } from "./dictionaries/ar";
import { en, enPlurals } from "./dictionaries/en";
import { interpolate, selectPlural } from "./translate";

describe("interpolate", () => {
  it("fills named tokens", () => {
    expect(interpolate("Welcome, {name}", { name: "Ali" })).toBe("Welcome, Ali");
  });

  it("stringifies numeric params", () => {
    expect(interpolate("{count} photos", { count: 3 })).toBe("3 photos");
  });

  it("leaves unknown tokens untouched and returns plain templates as-is", () => {
    expect(interpolate("Hi {missing}", { name: "x" })).toBe("Hi {missing}");
    expect(interpolate("no tokens")).toBe("no tokens");
  });
});

describe("selectPlural", () => {
  it("uses English one/other", () => {
    expect(selectPlural(enPlurals.images, "en", 1)).toBe("{count} photo");
    expect(selectPlural(enPlurals.images, "en", 5)).toBe("{count} photos");
  });

  it("resolves the full Arabic category set", () => {
    expect(selectPlural(arPlurals.images, "ar", 0)).toBe("لا صور");
    expect(selectPlural(arPlurals.images, "ar", 1)).toBe("صورة واحدة");
    expect(selectPlural(arPlurals.images, "ar", 2)).toBe("صورتان");
    expect(selectPlural(arPlurals.images, "ar", 3)).toBe("{count} صور");
    expect(selectPlural(arPlurals.images, "ar", 11)).toBe("{count} صورة");
  });

  it("falls back to `other` when a category form is absent", () => {
    // deleteScans only defines `other`; every count must resolve to it.
    expect(selectPlural(arPlurals.deleteScans, "ar", 2)).toBe("حذف ({count})");
  });
});

describe("dictionary parity", () => {
  it("Arabic covers every English key (and no extras)", () => {
    expect(Object.keys(ar).sort()).toEqual(Object.keys(en).sort());
  });

  it("every plural base exists in both locales with an `other` form", () => {
    for (const key of Object.keys(enPlurals) as (keyof typeof enPlurals)[]) {
      expect(arPlurals[key]?.other).toBeTruthy();
    }
  });
});
