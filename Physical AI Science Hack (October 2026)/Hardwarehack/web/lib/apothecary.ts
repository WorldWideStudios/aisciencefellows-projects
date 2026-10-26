// Types and pure helpers for the concoction console. The API is the source of truth for rules;
// these helpers only drive what the screen shows while someone edits.

export const COLUMNS = 12;
export const WELL_CAPACITY_UL = 200;
export const MIN_DRAW_UL = 5;

export interface Trough { trough: number; name: string; color: string; volume_ul: number | null }
export interface Ingredient { trough: number; volume_ul: number }
export interface Recipe { column: number; name: string; ingredients: Ingredient[] }
export interface Brewed { name: string; ingredients: Ingredient[]; brewed: string; run_id: string }
export interface ConsoleState {
  troughs: Trough[];
  tips: { small_next: number; large_next: number; small_left: number; large_left: number };
  columns: Record<string, Brewed>;
  robot: { host: string; mock: boolean };
  calibrated: boolean;
}
export interface PlanResult {
  problems: string[];
  summary: { small_tips: number; large_tips: number; trough_draw_ul: Record<string, number>; column_totals: Record<string, number> };
  simulation: { ok: boolean; steps: number; error: string } | null;
}

export const total = (ingredients: Ingredient[]) => ingredients.reduce((sum, i) => sum + (i.volume_ul || 0), 0);

/** Recipes worth sending: ones with at least one ingredient. */
export const orderable = (drafts: Record<number, Recipe>) =>
  Object.values(drafts).filter((r) => r.ingredients.length > 0).sort((a, b) => a.column - b.column);

/** µL as a short readable string: 1250 -> "1.25 mL", 40 -> "40 µL". */
export function formatVolume(ul: number | null | undefined): string {
  if (ul === null || ul === undefined) return "not set";
  return ul >= 1000 ? `${Number((ul / 1000).toPrecision(3))} mL` : `${Number(ul.toPrecision(3))} µL`;
}

/** Name for a concoction nobody named yet: follows the plate name, e.g. "Batch 2 column 3". */
export const defaultName = (plate: string, column: number) => `${plate} column ${column}`;

/** Recipes as sent to the API: unnamed ones carry their default name. */
export const withDefaultNames = (plate: string, recipes: Recipe[]) =>
  recipes.map((r) => (r.name.trim() ? r : { ...r, name: defaultName(plate, r.column) }));

export interface Slice { trough: number; start: number; end: number }

/** The well's contents as pie slices (fractions 0-1 of the circle), one per trough, in recipe order. */
export function pieSlices(ingredients: Ingredient[]): Slice[] {
  const byTrough = new Map<number, number>();
  for (const i of ingredients) if (i.volume_ul > 0) byTrough.set(i.trough, (byTrough.get(i.trough) ?? 0) + i.volume_ul);
  const sum = [...byTrough.values()].reduce((a, b) => a + b, 0);
  let start = 0;
  return [...byTrough].map(([trough, volume]) => {
    const slice = { trough, start, end: start + volume / sum };
    start = slice.end;
    return slice;
  });
}

const fmt = (v: number) => `${Number(v.toFixed(3))}`;

/** SVG path of one slice, starting at 12 o'clock and going clockwise. */
export function slicePath(cx: number, cy: number, r: number, start: number, end: number): string {
  const point = (t: number) => [cx + r * Math.sin(2 * Math.PI * t), cy - r * Math.cos(2 * Math.PI * t)].map(fmt).join(" ");
  const large = end - start > 0.5 ? 1 : 0;
  return `M${fmt(cx)} ${fmt(cy)} L${point(start)} A${fmt(r)} ${fmt(r)} 0 ${large} 1 ${point(end)} Z`;
}
