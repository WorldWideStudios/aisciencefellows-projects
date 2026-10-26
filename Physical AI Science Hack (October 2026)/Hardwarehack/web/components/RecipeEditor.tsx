"use client";
// Recipe for the selected plate column: ingredients in the order they're added to the well.
import { defaultName, MIN_DRAW_UL, total, WELL_CAPACITY_UL, type Recipe, type Trough } from "@/lib/apothecary";

interface Props {
  column: number;
  plate: string;
  recipe: Recipe;
  brewed?: { name: string; ingredients: { trough: number; volume_ul: number }[]; brewed: string };
  troughs: Trough[];
  onChange: (recipe: Recipe) => void;
}

export default function RecipeEditor({ column, plate, recipe, brewed, troughs, onChange }: Props) {
  const name = (trough: number) => troughs.find((t) => t.trough === trough)?.name ?? `Trough ${trough}`;
  const tint = (trough: number) => troughs.find((t) => t.trough === trough)?.color ?? "#999";

  if (brewed) {
    return (
      <section aria-labelledby="recipe-title">
        <h2 id="recipe-title" className="section-title">Column {column}: {brewed.name || "unnamed concoction"}</h2>
        <p className="mb-2 text-xs text-ink-soft">Brewed {brewed.brewed.replace("T", " at ")}. This column is done; start a new plate to use it again.</p>
        <ul className="flex flex-col gap-1 text-sm">
          {brewed.ingredients.map((i, k) => (
            <li key={k} className="flex items-center gap-2">
              <span className="size-3 rounded-full" style={{ background: tint(i.trough) }} />{name(i.trough)}
              <span className="ml-auto text-ink-soft">{i.volume_ul} µL</span>
            </li>
          ))}
        </ul>
      </section>
    );
  }

  const sum = total(recipe.ingredients);
  const over = sum > WELL_CAPACITY_UL;
  const update = (index: number, patch: Partial<{ trough: number; volume_ul: number }>) =>
    onChange({ ...recipe, ingredients: recipe.ingredients.map((ing, k) => (k === index ? { ...ing, ...patch } : ing)) });

  return (
    <section aria-labelledby="recipe-title">
      <h2 id="recipe-title" className="section-title">{recipe.name.trim() || defaultName(plate, column)}</h2>
      <p className="mb-2 text-xs text-ink-soft">Column {column}: wells A to H all get this recipe. At least {MIN_DRAW_UL} µL per ingredient, a fresh tip for each.</p>
      <input className="field mb-2" placeholder={defaultName(plate, column)} maxLength={80} value={recipe.name}
             aria-label="Concoction name" onChange={(e) => onChange({ ...recipe, name: e.target.value })} />
      {recipe.ingredients.length === 0 ? (
        <p className="rounded-md border border-dashed border-mithril px-3 py-3 text-xs text-ink-soft">
          No ingredients yet. Use Add next to a trough, or add one here.
        </p>
      ) : (
        <ol className="flex flex-col gap-1.5">
          {recipe.ingredients.map((ing, k) => (
            <li key={k} className="grid grid-cols-[auto_1fr_5.5rem_auto] items-center gap-1.5">
              <span className="size-3 rounded-full" style={{ background: tint(ing.trough) }} />
              <select className="field" value={ing.trough} aria-label={`Ingredient ${k + 1} trough`}
                      onChange={(e) => update(k, { trough: Number(e.target.value) })}>
                {troughs.map((t) => <option key={t.trough} value={t.trough}>{t.trough}. {t.name}</option>)}
              </select>
              <label className="flex items-center gap-1 text-sm text-ink-soft">
                <input className={`field text-right ${ing.volume_ul < MIN_DRAW_UL ? "border-alert" : ""}`} inputMode="decimal"
                       aria-label={`Ingredient ${k + 1} microlitres`} value={Number.isFinite(ing.volume_ul) ? ing.volume_ul : ""}
                       onChange={(e) => update(k, { volume_ul: parseFloat(e.target.value.replace(",", ".")) || 0 })} />
                µL
              </label>
              <button className="btn btn-quiet" aria-label={`Remove ingredient ${k + 1}`}
                      onClick={() => onChange({ ...recipe, ingredients: recipe.ingredients.filter((_, i) => i !== k) })}>Remove</button>
            </li>
          ))}
        </ol>
      )}
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <button className="btn" onClick={() => onChange({ ...recipe, ingredients: [...recipe.ingredients, { trough: 1, volume_ul: 10 }] })}>
          Add ingredient
        </button>
        {recipe.ingredients.length > 0 && (
          <button className="btn btn-quiet" onClick={() => onChange({ ...recipe, ingredients: [] })}>Clear column</button>
        )}
        <div className="ml-auto w-36">
          <div className="h-2 overflow-hidden rounded-full bg-mithril-soft" role="meter" aria-valuemin={0}
               aria-valuemax={WELL_CAPACITY_UL} aria-valuenow={sum} aria-label="Volume per well">
            <div className={`h-full ${over ? "bg-alert" : "bg-leaf"}`} style={{ width: `${Math.min(sum / WELL_CAPACITY_UL, 1) * 100}%` }} />
          </div>
          <div className={`mt-1 text-right text-xs ${over ? "text-alert" : "text-ink-soft"}`}>
            {Number(sum.toPrecision(4))} of {WELL_CAPACITY_UL} µL per well
          </div>
        </div>
      </div>
    </section>
  );
}
