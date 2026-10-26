import { describe, expect, it } from "vitest";
import { MIN_DRAW_UL, total, WELL_CAPACITY_UL } from "./apothecary";
import { DEFAULT_TEMPLATE_ID, TEMPLATES, templateDrafts } from "./templates";

describe("order templates", () => {
  it("default to the single-agent panel", () => {
    expect(TEMPLATES.find((t) => t.id === DEFAULT_TEMPLATE_ID)?.name).toBe("Single-agent panel");
  });

  it("control with the DMSO vehicle, not plain saline", () => {
    for (const template of TEMPLATES) {
      for (const control of template.recipes.filter((r) => /control/i.test(r.name))) {
        expect(control.name).toBe("DMSO vehicle control");
        expect(control.ingredients.some((i) => i.trough === 11)).toBe(true);  // 11 = DMSO vehicle
      }
    }
    expect(TEMPLATES.find((t) => t.id === "dox-dose")!.recipes.at(-1)!.name).toBe("DMSO vehicle control");
  });

  it("are oncology panels", () => {
    expect(TEMPLATES.map((t) => t.name)).toEqual(["Single-agent panel", "Combination regimens", "Doxorubicin dose response"]);
  });

  it("have unique ids and names", () => {
    expect(new Set(TEMPLATES.map((t) => t.id)).size).toBe(TEMPLATES.length);
    expect(TEMPLATES.length).toBeGreaterThanOrEqual(3);
  });

  it.each(TEMPLATES.map((t) => [t.name, t]))("%s respects the robot's rules", (_, template) => {
    const columns = template.recipes.map((r) => r.column);
    expect(new Set(columns).size).toBe(columns.length);
    for (const r of template.recipes) {
      expect(r.name.length).toBeGreaterThan(0);
      expect(total(r.ingredients)).toBeLessThanOrEqual(WELL_CAPACITY_UL);
      for (const i of r.ingredients) {
        expect(i.volume_ul).toBeGreaterThanOrEqual(MIN_DRAW_UL);
        expect(i.trough).toBeGreaterThanOrEqual(1);
        expect(i.trough).toBeLessThanOrEqual(12);
      }
    }
    const draws = template.recipes.flatMap((r) => r.ingredients);
    expect(draws.filter((i) => i.volume_ul <= 50).length).toBeLessThanOrEqual(12); // one rack of 50 µL tips
    expect(draws.filter((i) => i.volume_ul > 50).length).toBeLessThanOrEqual(12);  // one rack of 1000 µL tips
  });

  it("fills columns 1.. by default and the free columns when given", () => {
    const first = TEMPLATES[0];
    expect(Object.keys(templateDrafts(first.id)).map(Number)).toEqual(first.recipes.map((_, i) => i + 1));
    const placed = templateDrafts(first.id, [2, 5, 6, 9]);
    expect(Object.keys(placed).map(Number)).toEqual([2, 5, 6, 9]);
    expect(placed[5].name).toBe(first.recipes[1].name);
    expect(Object.keys(templateDrafts(first.id, [11, 12])).map(Number)).toEqual([11, 12]);
  });

  it("returns fresh copies", () => {
    const a = templateDrafts(TEMPLATES[0].id);
    a[1].ingredients[0].volume_ul = 999;
    expect(templateDrafts(TEMPLATES[0].id)[1].ingredients[0].volume_ul).not.toBe(999);
  });

  it("refuses an unknown template", () => {
    expect(() => templateDrafts("nope")).toThrow();
  });
});

describe("recognising a plate's template from its recipes", () => {
  it("finds an unedited template wherever its columns ended up", async () => {
    const { inferTemplate, draftsSignature } = await import("./templates");
    const drafts = templateDrafts("single");
    expect(inferTemplate(drafts)).toEqual({ id: "single", snapshot: draftsSignature(drafts) });
    const moved = templateDrafts("combos", [3, 7, 8, 9]);  // all 4 recipes, moved to free columns
    expect(inferTemplate(moved)?.id).toBe("combos");
    expect(inferTemplate(moved)?.snapshot).toBe(draftsSignature(moved));
  });

  it("marks it edited when volumes changed or recipes were removed", async () => {
    const { inferTemplate, draftsSignature } = await import("./templates");
    const drafts = templateDrafts("single");
    drafts[1].ingredients[0].volume_ul = 45;
    expect(inferTemplate(drafts)?.id).toBe("single");
    expect(inferTemplate(drafts)?.snapshot).not.toBe(draftsSignature(drafts));
    const fewer = templateDrafts("single");
    delete fewer[6];
    expect(inferTemplate(fewer)?.snapshot).not.toBe(draftsSignature(fewer));
  });

  it("finds nothing for hand-made or empty orders", async () => {
    const { inferTemplate } = await import("./templates");
    expect(inferTemplate({ 1: { column: 1, name: "My own brew", ingredients: [{ trough: 1, volume_ul: 10 }] } })).toBeNull();
    expect(inferTemplate({})).toBeNull();
  });

  it("signature ignores key order but not contents", async () => {
    const { draftsSignature } = await import("./templates");
    const a = { 1: { column: 1, name: "X", ingredients: [{ trough: 1, volume_ul: 10 }] } };
    const b = { 1: { ingredients: [{ volume_ul: 10, trough: 1 }], name: "X", column: 1 } };
    expect(draftsSignature(a)).toBe(draftsSignature(b));
    expect(draftsSignature(a)).not.toBe(draftsSignature({ 1: { ...a[1], name: "Y" } }));
  });
});
