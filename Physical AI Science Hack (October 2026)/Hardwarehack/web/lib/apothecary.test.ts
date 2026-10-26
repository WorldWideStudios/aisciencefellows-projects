import { describe, expect, it } from "vitest";
import { formatVolume, orderable, total } from "./apothecary";

describe("apothecary helpers", () => {
  it("totals a recipe", () => {
    expect(total([{ trough: 1, volume_ul: 40 }, { trough: 2, volume_ul: 10 }])).toBe(50);
  });
  it("keeps only recipes with ingredients, in column order", () => {
    const drafts = {
      3: { column: 3, name: "", ingredients: [{ trough: 1, volume_ul: 10 }] },
      1: { column: 1, name: "", ingredients: [] },
      2: { column: 2, name: "", ingredients: [{ trough: 2, volume_ul: 10 }] },
    };
    expect(orderable(drafts).map((r) => r.column)).toEqual([2, 3]);
  });
  it("formats volumes", () => {
    expect(formatVolume(40)).toBe("40 µL");
    expect(formatVolume(12000)).toBe("12 mL");
    expect(formatVolume(null)).toBe("not set");
  });
});

describe("default concoction names", () => {
  it("follow the plate and column until someone types a name", async () => {
    const { defaultName, withDefaultNames } = await import("./apothecary");
    expect(defaultName("Batch 2", 3)).toBe("Batch 2 column 3");
    const named = withDefaultNames("Batch 2", [
      { column: 1, name: "", ingredients: [{ trough: 1, volume_ul: 10 }] },
      { column: 2, name: "  ", ingredients: [{ trough: 1, volume_ul: 10 }] },
      { column: 3, name: "Cisplatin in saline", ingredients: [{ trough: 1, volume_ul: 10 }] },
    ]);
    expect(named.map((r) => r.name)).toEqual(["Batch 2 column 1", "Batch 2 column 2", "Cisplatin in saline"]);
  });
});

describe("pie slices for a well", () => {
  it("split the circle by volume, in recipe order", async () => {
    const { pieSlices } = await import("./apothecary");
    const slices = pieSlices([{ trough: 5, volume_ul: 30 }, { trough: 1, volume_ul: 10 }]);
    expect(slices.map((s) => s.trough)).toEqual([5, 1]);
    expect(slices[0].start).toBeCloseTo(0);
    expect(slices[0].end).toBeCloseTo(0.75);
    expect(slices[1].start).toBeCloseTo(0.75);
    expect(slices[1].end).toBeCloseTo(1);
  });
  it("merges repeated troughs and skips empty ones", async () => {
    const { pieSlices } = await import("./apothecary");
    const slices = pieSlices([{ trough: 2, volume_ul: 10 }, { trough: 3, volume_ul: 0 }, { trough: 2, volume_ul: 10 }]);
    expect(slices).toEqual([{ trough: 2, start: 0, end: 1 }]);
    expect(pieSlices([])).toEqual([]);
  });
  it("draws a slice as an SVG path from 12 o'clock, clockwise", async () => {
    const { slicePath } = await import("./apothecary");
    // a quarter slice of a radius-10 circle at (0, 0): from the top to the right
    expect(slicePath(0, 0, 10, 0, 0.25)).toBe("M0 0 L0 -10 A10 10 0 0 1 10 0 Z");
  });
});
