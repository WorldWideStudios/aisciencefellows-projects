"use client";
// The Armadillo 96-well PCR plate, top down. One recipe per column (wells A-H), because the
// 8-channel fills a whole column at once. Under each column, its recipe drawn to scale.
import { COLUMNS, pieSlices, slicePath, total, WELL_CAPACITY_UL, type Ingredient, type Recipe, type Trough } from "@/lib/apothecary";

const ROWS = "ABCDEFGH";
const PITCH = 46;
const PAD_X = 40;
const PAD_Y = 34;
const WELL_R = 17;
const PLATE_W = PAD_X + COLUMNS * PITCH + 18;
const PLATE_H = PAD_Y + ROWS.length * PITCH + 14;
const GLASS_H = 96;

interface Props {
  troughs: Trough[];
  drafts: Record<number, Recipe>;
  brewed: Record<string, { name: string; ingredients: Ingredient[] }>;
  selected: number;
  justBrewed: number[];
  onSelect: (column: number) => void;
}

export default function PlateView({ troughs, drafts, brewed, selected, justBrewed, onSelect }: Props) {
  const tint = (trough: number) => troughs.find((t) => t.trough === trough)?.color ?? "#999";
  return (
    <svg viewBox={`0 0 ${PLATE_W} ${PLATE_H + GLASS_H + 36}`} className="h-full w-full" preserveAspectRatio="xMidYMin meet" role="group" aria-label="Armadillo 96-well plate, 12 columns">
      <defs>
        <linearGradient id="glass" x1="0" x2="1">
          <stop offset="0" stopColor="#ffffff" stopOpacity="0.16" />
          <stop offset="0.4" stopColor="#ffffff" stopOpacity="0" />
        </linearGradient>
      </defs>
      {/* plate body and skirt */}
      <rect x={4} y={4} width={PLATE_W - 8} height={PLATE_H - 8} rx={14} fill="var(--color-plate)" stroke="var(--color-mithril)" strokeWidth={2} />
      <rect x={14} y={14} width={PLATE_W - 28} height={PLATE_H - 28} rx={8} fill="none" stroke="var(--color-mithril-soft)" strokeWidth={1.5} />
      <path d={`M4 30 L22 12`} stroke="var(--color-mithril)" strokeWidth={2} />

      {Array.from({ length: COLUMNS }, (_, c) => {
        const column = c + 1;
        const done = brewed[String(column)];
        const ingredients = done?.ingredients ?? drafts[column]?.ingredients ?? [];
        const volume = total(ingredients);
        const slices = pieSlices(ingredients);
        const x = PAD_X + c * PITCH + PITCH / 2;
        const isSelected = column === selected;
        const flashIndex = justBrewed.indexOf(column);
        let stackY = PLATE_H + 14 + GLASS_H;
        return (
          <g key={column} className="plate-column cursor-pointer" onClick={() => onSelect(column)}
             role="button" tabIndex={0} aria-pressed={isSelected}
             aria-label={`Column ${column}${done ? `, brewed: ${done.name || "unnamed"}` : volume ? `, ${volume} µL planned` : ", empty"}`}
             onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(column); } }}>
            <rect className="column-band" x={x - PITCH / 2 + 3} y={PAD_Y - 22} width={PITCH - 6} height={ROWS.length * PITCH + 24} rx={10}
                  fill={isSelected ? "var(--color-leaf-wash)" : "transparent"} stroke={isSelected ? "var(--color-leaf)" : "none"} strokeWidth={1.5} />
            <text x={x} y={PAD_Y - 8} textAnchor="middle" fontSize={12} fill={isSelected ? "var(--color-leaf-deep)" : "var(--color-ink-soft)"}>{column}</text>
            {[...ROWS].map((row, r) => {
              const y = PAD_Y + r * PITCH + PITCH / 2;
              const fill = Math.min(volume / WELL_CAPACITY_UL, 1);
              return (
                <g key={row}>
                  <circle cx={x} cy={y} r={WELL_R} fill="var(--color-well)" stroke="var(--color-mithril)" strokeWidth={1.5} />
                  {slices.length > 0 && (
                    // The well's contents as a pie: one slice per trough, sized by volume; the pie
                    // itself grows with how full the well is.
                    <g fillOpacity={done ? 1 : 0.85} className={flashIndex >= 0 ? "brew-flash" : undefined}
                       style={flashIndex >= 0 ? { animationDelay: `${flashIndex * 140}ms` } : undefined}>
                      {slices.length === 1
                        ? <circle cx={x} cy={y} r={4 + (WELL_R - 5) * Math.sqrt(fill)} fill={tint(slices[0].trough)} />
                        : slices.map((slice) => (
                            <path key={slice.trough} d={slicePath(x, y, 4 + (WELL_R - 5) * Math.sqrt(fill), slice.start, slice.end)}
                                  fill={tint(slice.trough)} stroke="var(--color-well)" strokeWidth={0.75} />
                          ))}
                    </g>
                  )}
                </g>
              );
            })}
            {/* the column's recipe as a glass of layers, to scale against one well */}
            <rect x={x - 12} y={PLATE_H + 14} width={24} height={GLASS_H} rx={5} fill="var(--color-well)" stroke="var(--color-mithril)" strokeWidth={1.5} />
            {ingredients.map((ingredient, i) => {
              const h = (ingredient.volume_ul / WELL_CAPACITY_UL) * (GLASS_H - 4);
              stackY -= h;
              return <rect key={i} x={x - 10} y={stackY - 2} width={20} height={Math.max(h, 0)} fill={tint(ingredient.trough)} fillOpacity={done ? 0.95 : 0.7} />;
            })}
            <rect x={x - 12} y={PLATE_H + 14} width={24} height={GLASS_H} rx={5} fill="url(#glass)" />
            <text x={x} y={PLATE_H + GLASS_H + 32} textAnchor="middle" fontSize={11} fill={volume > WELL_CAPACITY_UL ? "var(--color-alert)" : "var(--color-ink-soft)"}>
              {done ? "brewed" : volume ? `${Number(volume.toPrecision(3))} µL` : ""}
            </text>
          </g>
        );
      })}
      {[...ROWS].map((row, r) => (
        <text key={row} x={PAD_X - 14} y={PAD_Y + r * PITCH + PITCH / 2 + 4} textAnchor="middle" fontSize={12} fill="var(--color-ink-soft)">{row}</text>
      ))}
    </svg>
  );
}
