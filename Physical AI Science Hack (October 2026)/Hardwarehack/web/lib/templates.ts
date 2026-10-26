// Ready-made orders for demos. Trough numbers refer to the default trough names
// (1 0.9% Saline, 2 Methotrexate, 3 5% Dextrose (D5W), 4 Doxorubicin, 5 Paclitaxel,
// 6 Sterile Water, 7 5-Fluorouracil, 8 Cisplatin, 9 Epirubicin, 10 PBS buffer,
// 11 DMSO vehicle, 12 Carboplatin). Demo mixtures only: the volumes are not dosing guidance.
// Every template stays within the robot's rules: ≥ 5 µL per draw, ≤ 200 µL per well,
// and at most one rack (12 columns) of each tip size.
import type { Recipe } from "./apothecary";

export interface Template { id: string; name: string; recipes: Recipe[] }

/** Template a plate starts with the first time it's opened. */
export const DEFAULT_TEMPLATE_ID = "single";

const r = (column: number, name: string, ...parts: [number, number][]): Recipe =>
  ({ column, name, ingredients: parts.map(([trough, volume_ul]) => ({ trough, volume_ul })) });

export const TEMPLATES: Template[] = [
  { id: "single", name: "Single-agent panel", recipes: [
    r(1, "Doxorubicin in saline", [4, 20], [1, 80]),
    r(2, "Paclitaxel in D5W", [5, 20], [3, 80]),
    r(3, "Cisplatin in saline", [8, 25], [1, 75]),
    r(4, "5-Fluorouracil in saline", [7, 30], [1, 70]),
    r(5, "Methotrexate in PBS", [2, 15], [10, 85]),
    r(6, "DMSO vehicle control", [11, 5], [1, 95]),
  ] },
  { id: "combos", name: "Combination regimens", recipes: [
    r(1, "Paclitaxel + carboplatin", [5, 15], [12, 15], [3, 70]),
    r(2, "Cisplatin + 5-FU", [8, 20], [7, 20], [1, 60]),
    r(3, "Doxorubicin + paclitaxel", [4, 15], [5, 15], [3, 70]),
    r(4, "Epirubicin + 5-FU", [9, 15], [7, 15], [1, 70]),
  ] },
  { id: "dox-dose", name: "Doxorubicin dose response", recipes: [
    r(1, "Doxorubicin 1:2", [4, 50], [1, 50]),
    r(2, "Doxorubicin 1:4", [4, 25], [1, 75]),
    r(3, "Doxorubicin 1:8", [4, 12.5], [1, 87.5]),
    r(4, "Doxorubicin 1:16", [4, 6.25], [1, 93.75]),
    r(5, "DMSO vehicle control", [11, 5], [1, 95]),
  ] },
];

/**
 * A template's recipes as drafts keyed by column (fresh copies), placed in
 * ``freeColumns`` in order when given (columns that aren't brewed yet).
 */
export function templateDrafts(id: string, freeColumns?: number[]): Record<number, Recipe> {
  const template = TEMPLATES.find((t) => t.id === id);
  if (!template) throw new Error(`Unknown template: ${id}`);
  const columns = freeColumns ?? template.recipes.map((_, i) => i + 1);
  return Object.fromEntries(
    template.recipes.slice(0, columns.length).map((recipe, i) => [columns[i], { ...structuredClone(recipe), column: columns[i] }]),
  );
}

/** Contents of a draft order, independent of key order: used to tell whether a template was edited. */
export function draftsSignature(drafts: Record<number, Recipe>): string {
  return JSON.stringify(
    Object.values(drafts)
      .sort((a, b) => a.column - b.column)
      .map((r) => [r.column, r.name, r.ingredients.map((i) => [i.trough, i.volume_ul])]),
  );
}

/**
 * The template a draft order came from, recognised by its recipe names (for plates saved
 * before the template was recorded). ``snapshot`` is what the order would be unedited.
 */
export function inferTemplate(drafts: Record<number, Recipe>): { id: string; snapshot: string } | null {
  const recipes = Object.values(drafts).filter((r) => r.ingredients.length > 0);
  if (recipes.length === 0) return null;
  for (const template of TEMPLATES) {
    const byName = new Map(template.recipes.map((t) => [t.name, t]));
    if (!recipes.every((r) => byName.has(r.name))) continue;
    // Expected order: every template recipe, in the columns the drafts use (in order).
    const columns = [...recipes].sort((a, b) => a.column - b.column).map((r) => r.column);
    const placed = templateDrafts(template.id, columns);
    const complete = recipes.length === template.recipes.length;
    return { id: template.id, snapshot: draftsSignature(complete ? placed : templateDrafts(template.id)) };
  }
  return null;
}
