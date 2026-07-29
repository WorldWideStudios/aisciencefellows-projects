// Canvas for the `cfps_mastermix` workflow.
//
// Run-setup UI for the OpenCFPS (SepiaBio) pipetting workflow. You:
//   - pick the deck objects (reagent cold block, destination plate, pipette, tips)
//   - assign each reagent + each master-mix tube to a cold-block hole (hole_1..10)
//   - choose which of the three master mixes to make (implied by well assignment)
//   - paint a 96-well plate map: which wells get Positive / Negative / Sample
//   - set the per-well volume, the safety-extra reactions, and the plasmid volume
//
// The panel shows the live volume calculations per mix and flags any pipetting
// step below the 0.5 uL minimum of the smaller pipette. Each transfer is routed
// by total volume — under 10 uL to the 10 uL pipette, otherwise to the 120 uL
// one — and only split into multiple strokes if it exceeds that pipette's max,
// so nothing here is capped; we just report strokes and tips per rack.
//
// Sandboxed iframe contract: only `react` may be imported, no network/FS, all host
// communication via the injected `zeon.*` globals; `export default` the component.
// Object inputs submit the world-object NAME (never a UUID).

import React, { useEffect, useMemo, useState } from "react";

// Live tip-box count pushed by the host (mirrors the frontend TipBox type).
// remaining = capacity - tip_index + 1; `active` marks the rack in use right now.
type TipBox = { uuid: string; name: string; type: string; tip_index: number; capacity: number; remaining: number; active: boolean };

declare const zeon: {
  schema: { name: string; type: string; description?: string; defaultValue?: unknown; is_array?: boolean }[];
  worldObjects: {
    uuid: string;
    name: string;
    displayName?: string;
    meshType?: string;
    anchors?: string[];
    // World pose (metres, quaternion wxyz). Present at run time; used by the map.
    pose?: { xyz: number[]; wxyz: number[] };
  }[];
  defaults: Record<string, unknown>;
  submit: (values: Record<string, unknown>) => void;
  onValidationErrors: (cb: (errs: { path: string; message: string }[]) => void) => void;
  // Live per-box tip counts: seeded once the host is ready, re-pushed on every
  // tip use / box reset. See onTipCounts to subscribe.
  tipBoxes: TipBox[];
  onTipCounts: (cb: (boxes: TipBox[]) => void) => void;
};

const HOLES = Array.from({ length: 10 }, (_, i) => `hole_${i + 1}`);
const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const COLS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
// Two pipettes with non-overlapping ranges (mirrors PIPETTES in skills/utils.py).
// A transfer under 10 uL goes to the 10 uL pipette, anything else to the 120 uL
// one — chosen on the TOTAL volume, before it is split into strokes.
const PIPETTES = {
  small: { name: "10 µL", min: 0.5, max: 10.0, box: "10 µL tips" },
  large: { name: "120 µL", min: 10.0, max: 120.0, box: "120 µL tips" },
};
// Smallest volume any pipette on the deck can place — below this nothing works.
const MIN_UL = PIPETTES.small.min;
const RECIPE_REF_UL = 10.0;

// Per-10uL-reference reaction recipe (kit's three columns). Sample DNA/water are
// filled from the plasmid-volume input at run time.
type Cond = "pos" | "neg" | "sample";
const COND_META: Record<Cond, { label: string; short: string; color: string }> = {
  pos: { label: "Positive control", short: "Pos", color: "#0F9D63" },
  neg: { label: "Negative control", short: "Neg", color: "#64748b" },
  sample: { label: "Sample (plasmid)", short: "Smp", color: "#0e7490" },
};

const objName = (o: { name?: string; displayName?: string; uuid: string }) =>
  o.displayName || o.name || o.uuid;

const wellKey = (w: string) => ROWS.indexOf(w[0]) * 12 + (parseInt(w.slice(1), 10) - 1);
const sortWells = (ws: string[]) => [...ws].sort((a, b) => wellKey(a) - wellKey(b));
const r4 = (n: number) => Math.round(n * 1e4) / 1e4;
const pipetteFor = (v: number) => (r4(v) < PIPETTES.large.min ? PIPETTES.small : PIPETTES.large);
const strokes = (v: number) => (v <= 0 ? 0 : Math.ceil(r4(v) / pipetteFor(v).max));

// Visual system — "benchtop worksheet": a near-monochrome ink-on-paper sheet
// where saturated colour appears only where it carries meaning (the plate-map
// conditions, warnings, and the single assay-green Run action). Technical voice
// in monospace for eyebrows / labels / table data; a clean sans for prose.
// Hairline rules and a crisp ledger header instead of boxed grey cards.
const SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
const MONO = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace";
const INK = "#16231C", MUTE = "#5B6B62", FAINT = "#94A29A";
const LINE = "#E3E8E3", HAIR = "#EFF2EF", PAPER = "#FCFCFA";
const GREEN = "#0F9D63", GREENSOFT = "#E8F5EE"; // sfGFP "expression / go" signal
const S: Record<string, React.CSSProperties> = {
  page: { fontFamily: SANS, color: INK, background: PAPER, padding: "34px 26px 46px", maxWidth: 720, margin: "0 auto", fontSize: 14, lineHeight: 1.55, WebkitFontSmoothing: "antialiased" },
  eyebrow: { fontFamily: MONO, fontSize: 11, fontWeight: 600, letterSpacing: 1.6, textTransform: "uppercase", color: MUTE, margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 },
  h1: { fontFamily: SANS, fontSize: 27, fontWeight: 800, letterSpacing: -0.7, lineHeight: 1.05, margin: "0 0 10px", color: INK },
  sub: { fontSize: 13.5, color: MUTE, margin: "0 0 4px", lineHeight: 1.6, maxWidth: "62ch" },
  rule: { height: 1, background: LINE, border: 0, margin: "22px 0 2px" },
  h2: { fontFamily: MONO, fontSize: 11, fontWeight: 700, margin: "36px 0 12px", paddingTop: 18, color: INK, textTransform: "uppercase", letterSpacing: 1.3, borderTop: `1px solid ${LINE}` },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 16px" },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, fontWeight: 600, margin: "12px 0 5px", color: MUTE, textTransform: "uppercase", letterSpacing: 0.6 },
  field: { width: "100%", boxSizing: "border-box", padding: "9px 11px", fontFamily: SANS, fontSize: 13.5, border: `1px solid ${LINE}`, borderRadius: 7, background: "#fff", color: INK, outline: "none" },
  card: { border: `1px solid ${LINE}`, borderRadius: 8, padding: 14, marginTop: 12, background: "#fff" },
  paintRow: { display: "flex", gap: 6, flexWrap: "wrap", margin: "8px 0 12px" },
  paintBtn: { fontFamily: MONO, padding: "6px 12px", fontSize: 11, fontWeight: 700, letterSpacing: 0.4, textTransform: "uppercase", border: `1px solid ${LINE}`, borderRadius: 6, cursor: "pointer", background: "#fff", color: INK },
  plate: { display: "inline-grid", gridTemplateColumns: `20px repeat(12, 27px)`, gap: 4, userSelect: "none" },
  hdr: { fontFamily: MONO, fontSize: 9.5, color: FAINT, textAlign: "center", lineHeight: "27px" },
  cell: { width: 27, height: 27, borderRadius: 5, border: `1px solid ${LINE}`, fontFamily: MONO, fontSize: 8.5, cursor: "pointer", color: "#fff", fontWeight: 700, padding: 0 },
  table: { width: "100%", borderCollapse: "collapse", fontFamily: SANS, fontSize: 12.5, marginTop: 10 },
  th: { fontFamily: MONO, textAlign: "right", padding: "7px 8px", borderBottom: `1.5px solid ${INK}`, color: MUTE, fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  thl: { fontFamily: MONO, textAlign: "left", padding: "7px 8px", borderBottom: `1.5px solid ${INK}`, color: MUTE, fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  td: { fontFamily: MONO, textAlign: "right", padding: "6px 8px", borderBottom: `1px solid ${HAIR}`, fontVariantNumeric: "tabular-nums" },
  tdl: { fontFamily: SANS, textAlign: "left", padding: "6px 8px", borderBottom: `1px solid ${HAIR}` },
  groupRow: { fontFamily: MONO, textAlign: "left", padding: "13px 8px 4px", fontSize: 10, fontWeight: 700, color: INK, textTransform: "uppercase", letterSpacing: 0.7, borderBottom: `1px solid ${LINE}` },
  warn: { background: "#FAF5E9", border: "1px solid #E6D6A8", borderRadius: 8, padding: "10px 13px", marginTop: 14, fontSize: 12.5, color: "#7A5B12", lineHeight: 1.5 },
  errorBox: { background: "#FBEEEB", border: "1px solid #E7C1B9", borderRadius: 8, padding: "11px 13px", marginTop: 14, fontSize: 13, color: "#8E2C1E", lineHeight: 1.5 },
  button: { width: "100%", marginTop: 24, padding: "14px 16px", fontFamily: SANS, fontSize: 14.5, fontWeight: 700, letterSpacing: 0.2, color: "#fff", background: GREEN, border: "none", borderRadius: 8, cursor: "pointer" },
  flag: { fontFamily: MONO, color: "#B42318", fontWeight: 700 },
  // --- collapsible "more info" disclosures + prose ---------------------------
  details: { border: `1px solid ${LINE}`, borderRadius: 8, marginTop: 12, background: "#fff", overflow: "hidden" },
  summary: { cursor: "pointer", listStyle: "none", padding: "11px 14px", fontFamily: MONO, fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase", color: INK, background: PAPER, userSelect: "none", display: "flex", alignItems: "center", gap: 8 },
  summaryTag: { fontFamily: MONO, fontSize: 9.5, fontWeight: 700, color: MUTE, background: "#fff", border: `1px solid ${LINE}`, borderRadius: 4, padding: "2px 7px", textTransform: "uppercase", letterSpacing: 0.5, whiteSpace: "nowrap", flexShrink: 0 },
  detailsBody: { padding: "12px 16px 16px", fontFamily: SANS, fontSize: 13, color: "#3A463F", lineHeight: 1.6 },
  h4: { fontFamily: MONO, fontSize: 10.5, fontWeight: 700, margin: "16px 0 6px", color: INK, textTransform: "uppercase", letterSpacing: 0.6 },
  p2: { margin: "7px 0", lineHeight: 1.6 },
  ul: { margin: "7px 0", paddingLeft: 20 },
  ol: { margin: "7px 0", paddingLeft: 20 },
  li: { marginBottom: 5 },
  quote: { borderLeft: `3px solid ${GREEN}`, padding: "9px 13px", background: GREENSOFT, borderRadius: "0 6px 6px 0", fontSize: 12.5, color: "#0B5A3A", margin: "11px 0", fontStyle: "italic" },
  code: { fontFamily: MONO, fontSize: 12, background: HAIR, borderRadius: 4, padding: "1px 5px", color: INK },
  // --- workspace map ---------------------------------------------------------
  mapWrap: { margin: "16px 0 4px" },
  mapToggle: { display: "inline-flex", alignItems: "center", gap: 8, padding: "9px 14px", fontFamily: MONO, fontSize: 11, fontWeight: 700, letterSpacing: 0.5, textTransform: "uppercase", color: INK, background: "#fff", border: `1px solid ${LINE}`, borderRadius: 8, cursor: "pointer" },
  mapCard: { border: `1px solid ${LINE}`, borderRadius: 8, padding: 16, marginTop: 10, background: "#fff", display: "flex", flexWrap: "wrap", gap: "12px 20px", alignItems: "flex-start" },
  mapCol: { flex: "1 1 340px", minWidth: 280 },
  legendCol: { flex: "1 1 200px", minWidth: 185, maxHeight: 320, overflowY: "auto" },
  catRow: { display: "flex", flexWrap: "wrap", gap: 6, flexBasis: "100%", marginBottom: 2 },
};

const strDefault = (k: string, fb: string) => (typeof zeon.defaults?.[k] === "string" ? (zeon.defaults[k] as string) : fb);
const numDefault = (k: string, fb: number) => (typeof zeon.defaults?.[k] === "number" ? (zeon.defaults[k] as number) : fb);

// Collapsible "more info" disclosure — native <details> so it needs no state and
// stays accessible. `tag` is an optional pill on the right of the summary line.
function Info({ title, tag, defaultOpen, children }: { title: string; tag?: string; defaultOpen?: boolean; children: React.ReactNode }) {
  return (
    <details style={S.details} open={defaultOpen}>
      <summary style={S.summary}>
        <span style={{ flex: 1 }}>{title}</span>
        {tag ? <span style={S.summaryTag}>{tag}</span> : null}
      </summary>
      <div style={S.detailsBody}>{children}</div>
    </details>
  );
}

// ---------------------------------------------------------------------------
// Workspace map — a toggleable top-down plan of the deck. Reads live world
// poses from `zeon.worldObjects` (pose.xyz in metres) and plots each object as a
// category-coloured pin. The object NAMES live in the linked legend beside the
// map (and pop up on hover), so the plan itself never fills with overlapping
// text — the cells only ever carry a small index. Only real deck contents are
// shown (plates, tips, cold block, pipettes, the three instruments); holders,
// fixtures, and table surfaces are dropped so the plan stays clean and aligned.
// ---------------------------------------------------------------------------
type CatKey = "plates" | "tips" | "coldblock" | "pipettes" | "instruments" | "surfaces" | "other" | "holders";
const CAT_ORDER: CatKey[] = ["plates", "tips", "coldblock", "pipettes", "instruments", "surfaces", "other", "holders"];
const CAT_META: Record<CatKey, { label: string; color: string; defaultOn: boolean }> = {
  plates: { label: "Well plates", color: "#0E7490", defaultOn: true },
  tips: { label: "Tip boxes", color: "#B45309", defaultOn: true },
  coldblock: { label: "Cold block", color: "#3730A3", defaultOn: true },
  pipettes: { label: "Pipettes", color: "#9D174D", defaultOn: true },
  instruments: { label: "Instruments", color: "#15803D", defaultOn: true },
  surfaces: { label: "Table / surface", color: "#a8a29e", defaultOn: true },
  other: { label: "Other", color: "#64748b", defaultOn: true },
  holders: { label: "Holders & fixtures", color: "#cbd5e1", defaultOn: false },
};
// The map only ever shows real deck contents the operator reasons about:
// plates, tip boxes, the cold block, pipettes, and the three instruments.
// Everything else (holders, fixtures, table surfaces) is dropped so the plan
// stays legible and the pipettes / tip boxes read as clean aligned rows.
const MAP_CATS: CatKey[] = ["plates", "tips", "coldblock", "pipettes", "instruments"];
// Order matters: holders/stands/fixtures are checked first so a
// "wellplate_holder_…" lands in Holders, not Well plates. Objects without a
// meshType (deck surfaces like table_back) fall back to their name.
function classifyCat(meshType?: string, name?: string): CatKey {
  const t = ((meshType || name) || "").toLowerCase();
  if (/holder|stand|fixture/.test(t)) return "holders";
  if (/table|bench|surface|base_filter/.test(t)) return "surfaces";
  if (/reader|sealer|shaker/.test(t)) return "instruments";
  if (/tipbox/.test(t)) return "tips";
  if (/coldblock/.test(t)) return "coldblock";
  if (/epipette|pipette/.test(t)) return "pipettes";
  if (/wellplate/.test(t)) return "plates";
  return "other";
}

function WorkspaceMap() {
  const [open, setOpen] = useState(false);
  const [hovered, setHovered] = useState<string | null>(null);

  // Every object the host exposes with a world pose. (The backend already drops
  // the workspace-boundary walls, so what remains is real deck contents plus any
  // surfaces like table_back — those get the "surfaces" category via their name.)
  const objs = useMemo(
    () =>
      zeon.worldObjects
        .filter((o) => o.pose && Array.isArray(o.pose.xyz) && o.pose.xyz.length >= 2)
        .map((o) => ({
          uuid: o.uuid,
          name: objName(o),
          cat: classifyCat(o.meshType, objName(o)),
          x: o.pose!.xyz[0],
          y: o.pose!.xyz[1],
        }))
        .filter((o) => MAP_CATS.includes(o.cat)),
    [],
  );

  const presentCats = useMemo(() => {
    const s = new Set<CatKey>();
    objs.forEach((o) => s.add(o.cat));
    return CAT_ORDER.filter((c) => s.has(c));
  }, [objs]);

  const [visible, setVisible] = useState<Record<string, boolean>>(() => {
    const v: Record<string, boolean> = {};
    CAT_ORDER.forEach((c) => (v[c] = CAT_META[c].defaultOn));
    return v;
  });
  const toggleCat = (c: CatKey) => setVisible((s) => ({ ...s, [c]: !s[c] }));

  // Visible objects, numbered in a stable order (category, then name) so the
  // cells on the plan and the rows in the legend share the same index.
  const shown = useMemo(() => {
    const list = objs.filter((o) => visible[o.cat]);
    list.sort((a, b) => {
      const ci = CAT_ORDER.indexOf(a.cat) - CAT_ORDER.indexOf(b.cat);
      return ci !== 0 ? ci : a.name.localeCompare(b.name);
    });
    return list.map((o, i) => ({ ...o, n: i + 1 }));
  }, [objs, visible]);

  const shownByCat = useMemo(() => {
    const m: Record<string, typeof shown> = {};
    shown.forEach((o) => (m[o.cat] = m[o.cat] ? [...m[o.cat], o] : [o]));
    return m;
  }, [shown]);

  // Occupancy-grid layout. A lab deck is laid out in rows/columns — the 2x2
  // PCR-plate nest, the tip-box/pipette column — so instead of plotting raw
  // pixels (which jitter apart and break that alignment) we snap each object to
  // a grid cell. Columns/rows are found by 1-D gap clustering: coordinates within
  // TOL (~2.5 cm) collapse to one column/row, a real gap starts a new one. Ranks
  // preserve left→right / top→bottom order, so objects aligned in the world sit
  // in the same column/row on the map and land on clean grid lines. Every cell is
  // the SAME size; if two objects want the same cell (e.g. a holder under a plate,
  // or the tip box beside its pipette) the later one is bumped to the nearest free
  // cell — so a category's items are always drawn at one consistent size, never
  // squished. NB: absolute binning is avoided on purpose — it would split a column
  // whose members straddle a bin edge.
  const CELL = 30, PADX = 12, HEADER = 22, GAP = 3;
  const grid = useMemo(() => {
    if (!shown.length) return null;
    const TOL = 0.025; // metres
    const axis = (get: (o: any) => number) => {
      const vals = shown.map(get).sort((a, b) => a - b);
      const breaks: number[] = [];
      for (let i = 1; i < vals.length; i++) if (vals[i] - vals[i - 1] > TOL) breaks.push((vals[i] + vals[i - 1]) / 2);
      return { rank: (v: number) => breaks.reduce((r, b) => r + (v > b ? 1 : 0), 0), count: breaks.length + 1 };
    };
    const colAxis = axis((o) => o.x);
    const rowAxis = axis((o) => o.y);
    let C = colAxis.count, R = rowAxis.count;

    // Assign each object a distinct grid cell. Ideal cell first; on a clash, spiral
    // out to the nearest free cell (preferring the same row, then a step right).
    const taken = new Set<string>();
    const cellOf: Record<string, { c: number; r: number }> = {};
    const key = (c: number, r: number) => c + "," + r;
    shown.forEach((o) => {
      let c = colAxis.rank(o.x), r = R - 1 - rowAxis.rank(o.y); // flip so +Y is at top
      if (taken.has(key(c, r))) {
        let best: { c: number; r: number } | null = null, bestScore = Infinity;
        for (let rad = 1; rad <= C + R + 2 && !best; rad++) {
          for (let dr = -rad; dr <= rad; dr++) {
            for (let dc = -rad; dc <= rad; dc++) {
              if (Math.max(Math.abs(dc), Math.abs(dr)) !== rad) continue; // current ring only
              const nc = c + dc, nr = r + dr;
              if (nc < 0 || nr < 0 || taken.has(key(nc, nr))) continue;
              const dir = dr === 0 ? (dc > 0 ? 0 : 1) : dc === 0 ? 2 : 3; // right<left<vert<diag
              const score = (Math.abs(dc) + Math.abs(dr)) * 10 + dir;
              if (score < bestScore) { bestScore = score; best = { c: nc, r: nr }; }
            }
          }
          if (best) break;
        }
        if (best) { c = best.c; r = best.r; }
      }
      taken.add(key(c, r));
      cellOf[o.uuid] = { c, r };
      C = Math.max(C, c + 1); R = Math.max(R, r + 1);
    });

    const plotX = PADX, plotY = HEADER, gridW = C * CELL, gridH = R * CELL;
    const VBW = gridW + 2 * PADX, VBH = plotY + gridH + PADX;
    const rects: Record<string, { x: number; y: number; w: number; h: number }> = {};
    shown.forEach((o) => {
      const { c, r } = cellOf[o.uuid];
      rects[o.uuid] = { x: plotX + c * CELL + GAP, y: plotY + r * CELL + GAP, w: CELL - 2 * GAP, h: CELL - 2 * GAP };
    });
    return { rects, C, R, plotX, plotY, gridW, gridH, VBW, VBH };
  }, [shown]);

  return (
    <div style={S.mapWrap}>
      <button type="button" onClick={() => setOpen((v) => !v)} style={S.mapToggle}
              aria-expanded={open}>
        <span style={{ fontSize: 12, color: MUTE, width: 10 }}>{open ? "▾" : "▸"}</span>
        <span>Workspace map</span>
        <span style={{ fontSize: 11, fontWeight: 500, color: FAINT }}>
          · {objs.length} object{objs.length !== 1 ? "s" : ""}
        </span>
      </button>

      {open && (objs.length === 0 || !grid ? (
        <div style={S.mapCard}>
          <p style={{ ...S.sub, margin: 0 }}>
            No positioned objects to map in this world (poses unavailable).
          </p>
        </div>
      ) : (
        <div style={S.mapCard}>
          {/* category toggles (full-width first row) */}
          <div style={S.catRow}>
            {presentCats.map((c) => {
              const on = visible[c];
              const meta = CAT_META[c];
              const count = objs.filter((o) => o.cat === c).length;
              return (
                <button key={c} type="button" onClick={() => toggleCat(c)}
                        style={{
                          display: "inline-flex", alignItems: "center", gap: 6,
                          padding: "3px 10px", fontSize: 11.5, fontWeight: 600,
                          borderRadius: 999, cursor: "pointer",
                          border: `1px solid ${on ? meta.color : LINE}`,
                          background: on ? meta.color + "14" : "#fff",
                          color: on ? meta.color : FAINT,
                        }}>
                  <span style={{ width: 9, height: 9, borderRadius: 9, background: on ? meta.color : LINE }} />
                  {meta.label} <span style={{ opacity: 0.65, fontWeight: 700 }}>{count}</span>
                </button>
              );
            })}
          </div>

          {/* top-down deck plan, snapped to a grid */}
          <div style={S.mapCol}>
            <svg viewBox={`0 0 ${grid.VBW} ${grid.VBH}`} style={{ width: "100%", height: "auto", display: "block" }}
                 role="img" aria-label="Top-down grid map of the workspace deck">
              <text x={grid.plotX} y={13} fontFamily={MONO} fontSize={9} fill={FAINT} fontWeight={600} letterSpacing={0.4}>
                DECK LAYOUT · TOP VIEW (+X →, +Y ↑)
              </text>
              <rect x={grid.plotX} y={grid.plotY} width={grid.gridW} height={grid.gridH} rx={8}
                    fill={PAPER} stroke={LINE} />
              {Array.from({ length: grid.C + 1 }).map((_, i) => (
                <line key={"v" + i} x1={grid.plotX + i * CELL} y1={grid.plotY}
                      x2={grid.plotX + i * CELL} y2={grid.plotY + grid.gridH} stroke={HAIR} strokeWidth={1} />
              ))}
              {Array.from({ length: grid.R + 1 }).map((_, i) => (
                <line key={"h" + i} x1={grid.plotX} y1={grid.plotY + i * CELL}
                      x2={grid.plotX + grid.gridW} y2={grid.plotY + i * CELL} stroke={HAIR} strokeWidth={1} />
              ))}

              {/* one rectangle per object, sitting in its grid cell */}
              {shown.map((o) => {
                const r = grid.rects[o.uuid];
                if (!r) return null;
                const color = CAT_META[o.cat].color;
                const hl = hovered === o.uuid;
                return (
                  <g key={o.uuid} onMouseEnter={() => setHovered(o.uuid)} onMouseLeave={() => setHovered(null)}
                     style={{ cursor: "default" }}>
                    <rect x={r.x} y={r.y} width={r.w} height={r.h} rx={4}
                          fill={hl ? color : color + "1e"} stroke={color} strokeWidth={hl ? 2 : 1.4} />
                    <text x={r.x + r.w / 2} y={r.y + r.h / 2} textAnchor="middle" dominantBaseline="central"
                          fontSize={11} fontWeight={700} fill={hl ? "#fff" : color} pointerEvents="none">{o.n}</text>
                  </g>
                );
              })}

              {/* hovered name — one at a time, drawn on top so it never turns to mush */}
              {shown.filter((o) => hovered === o.uuid).map((o) => {
                const r = grid.rects[o.uuid];
                if (!r) return null;
                const cx = r.x + r.w / 2;
                const w = Math.min(grid.VBW - 4, Math.max(46, o.name.length * 6.1 + 16));
                const tx = Math.max(w / 2 + 2, Math.min(cx, grid.VBW - w / 2 - 2));
                const above = r.y > 24;
                const ty = above ? r.y - 9 : r.y + r.h + 9;
                return (
                  <g key={"tip" + o.uuid} pointerEvents="none">
                    <rect x={tx - w / 2} y={ty - 9} width={w} height={18} rx={5} fill={INK} />
                    <text x={tx} y={ty} textAnchor="middle" dominantBaseline="central"
                          fontSize={10} fontWeight={600} fill="#fff">{o.name}</text>
                  </g>
                );
              })}
            </svg>
          </div>

          {/* linked legend — the names live here, grouped by category */}
          <div style={S.legendCol}>
            {presentCats.filter((c) => visible[c]).length === 0 ? (
              <p style={{ ...S.sub, margin: 0 }}>All categories hidden — toggle one above.</p>
            ) : (
              presentCats.filter((c) => visible[c]).map((c) => (
                <div key={c} style={{ marginBottom: 9 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10.5, fontWeight: 700,
                                color: CAT_META[c].color, textTransform: "uppercase", letterSpacing: 0.4, marginBottom: 3 }}>
                    <span style={{ width: 8, height: 8, borderRadius: 8, background: CAT_META[c].color }} />
                    {CAT_META[c].label}
                  </div>
                  {(shownByCat[c] || []).map((o) => (
                    <div key={o.uuid}
                         onMouseEnter={() => setHovered(o.uuid)} onMouseLeave={() => setHovered(null)}
                         style={{ display: "flex", alignItems: "center", gap: 7, padding: "2px 6px",
                                  borderRadius: 6, fontSize: 12, lineHeight: 1.5, cursor: "default",
                                  background: hovered === o.uuid ? CAT_META[c].color + "1f" : "transparent",
                                  color: MUTE }}>
                      <span style={{ flex: "0 0 auto", width: 16, height: 16, borderRadius: 16,
                                     background: CAT_META[c].color, color: "#fff", fontSize: 8.5, fontWeight: 700,
                                     display: "inline-flex", alignItems: "center", justifyContent: "center" }}>{o.n}</span>
                      <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{o.name}</span>
                    </div>
                  ))}
                </div>
              ))
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CfpsMasterMixScreen() {
  // --- object pickers ---------------------------------------------------------
  const pick = (match: (m: string) => boolean, dfltKey: string, fallback: string) => {
    const all = zeon.worldObjects;
    const hits = all.filter((o) => match((o.meshType || "").toLowerCase()));
    const list = hits.length ? hits : all;
    // Prefer the host-provided default, else the hard-pinned fallback name; only
    // drop to "first in list" if neither is actually present in the world.
    const d = strDefault(dfltKey, fallback);
    if (d && list.some((o) => objName(o) === d)) return { list, init: d };
    if (fallback && list.some((o) => objName(o) === fallback)) return { list, init: fallback };
    return { list, init: list[0] ? objName(list[0]) : "" };
  };
  // Filters exclude holders/stands/coldblocks so each dropdown only offers real candidates.
  const pipetteP = useMemo(() => pick((m) => (m.includes("epipette") || m.includes("pipette")) && !m.includes("stand") && !m.includes("holder"), "pipette", "epipette_10ul"), []);
  const tipboxP = useMemo(() => pick((m) => m.includes("tipbox") && !m.includes("holder"), "tipbox", "tipbox_10ul_1"), []);
  const blockP = useMemo(() => pick((m) => m.includes("coldblock") && !m.includes("holder"), "reagent_block", "coldblock_wellplate"), []);
  const plateP = useMemo(() => pick((m) => m.includes("wellplate") && !m.includes("coldblock") && !m.includes("holder") && !m.includes("shaker"), "reaction_plate", "wellplate_96_flatbottom"), []);
  // Sealing + shaking hardware (used by the seal/shake steps appended after pipetting).
  const sealerP = useMemo(() => pick((m) => m.includes("sealer"), "platesealer", "platesealer_platemax_1"), []);
  const sealHolderP = useMemo(() => pick((m) => m.includes("seal_holder") || (m.includes("seal") && m.includes("holder")), "seal_holder", "seal_holder_stacked_reinforced_1"), []);
  const shakerP = useMemo(() => pick((m) => m.includes("shaker") && !m.includes("holder"), "shaker", "wellplate_shaker_1"), []);
  const plateHomeP = useMemo(() => pick((m) => m.includes("holder") && m.includes("wellplate"), "plate_home", "wellplate_holder_tags"), []);

  const [pipette, setPipette] = useState(pipetteP.init);
  const [tipbox, setTipbox] = useState(tipboxP.init);
  const [reagentBlock, setReagentBlock] = useState(blockP.init);
  const [reactionPlate, setReactionPlate] = useState(plateP.init);
  const [platesealer, setPlatesealer] = useState(sealerP.init);
  const [sealHolder, setSealHolder] = useState(sealHolderP.init);
  const [shaker, setShaker] = useState(shakerP.init);
  const [plateHome, setPlateHome] = useState(plateHomeP.init);
  const [shakerSlot, setShakerSlot] = useState(strDefault("shaker_slot", "slot_1"));
  // The shaker has no state sensor — the robot only knows what it was last told.
  // Default to "no" (stopped) and let the operator correct it.
  const [shakerRunning, setShakerRunning] = useState(strDefault("shaker_running", "no"));
  const [sealIndex, setSealIndex] = useState(numDefault("seal_index", 1));
  const [runName, setRunName] = useState(strDefault("run_name", "cfps_run"));

  // --- hole assignments -------------------------------------------------------
  const [holes, setHoles] = useState({
    extract_hole: strDefault("extract_hole", "hole_1"),
    buffer_hole: strDefault("buffer_hole", "hole_2"),
    ctrl_dna_hole: strDefault("ctrl_dna_hole", "hole_3"),
    sample_dna_hole: strDefault("sample_dna_hole", "hole_4"),
    water_hole: strDefault("water_hole", "hole_5"),
    pos_mm_hole: strDefault("pos_mm_hole", "hole_6"),
    neg_mm_hole: strDefault("neg_mm_hole", "hole_7"),
    sample_mm_hole: strDefault("sample_mm_hole", "hole_8"),
  });
  const setHole = (k: keyof typeof holes, v: string) => setHoles((h) => ({ ...h, [k]: v }));

  // --- scalars ----------------------------------------------------------------
  const [volPerWell, setVolPerWell] = useState(numDefault("vol_per_well", 20));
  const [extraUl, setExtraUl] = useState(numDefault("extra_volume_ul", 10));
  const [dnaStock, setDnaStock] = useState(numDefault("sample_dna_stock_nm", 200));
  const [dnaFinal, setDnaFinal] = useState(numDefault("sample_dna_final_nm", 4));
  // Sample DNA volume per 10 uL reference reaction, derived from the stock and the
  // target final conc (kit: 4 nM plasmid / 8 nM linear): V = final * 10 / stock.
  const sampleDnaVol = dnaStock > 0 ? r4((dnaFinal * RECIPE_REF_UL) / dnaStock) : 0;

  // --- plate map --------------------------------------------------------------
  const seed = () => {
    const m: Record<string, Cond> = {};
    (["pos", "neg", "sample"] as Cond[]).forEach((c) => {
      const dflt = strDefault(`${c === "sample" ? "sample" : c}_wells`, c === "pos" ? "A1" : c === "neg" ? "A2" : "A3,A4");
      dflt.split(",").map((w) => w.trim()).filter(Boolean).forEach((w) => (m[w] = c));
    });
    return m;
  };
  const [assign, setAssign] = useState<Record<string, Cond>>(seed);
  const [paint, setPaint] = useState<Cond | "erase">("pos");

  const paintWell = (w: string) =>
    setAssign((a) => {
      const next = { ...a };
      if (paint === "erase" || next[w] === paint) delete next[w];
      else next[w] = paint;
      return next;
    });

  const wellsOf = (c: Cond) => sortWells(Object.keys(assign).filter((w) => assign[w] === c));
  const counts = { pos: wellsOf("pos").length, neg: wellsOf("neg").length, sample: wellsOf("sample").length };

  const [errors, setErrors] = useState<string[]>([]);
  useEffect(() => {
    zeon.onValidationErrors((errs) => setErrors(errs.map((e) => e.message)));
  }, []);

  // Live tip-box counts (host-pushed). Seed from the initial snapshot, then
  // live-update as tips are consumed or a box is reset.
  const [tipBoxes, setTipBoxes] = useState<TipBox[]>(() => zeon.tipBoxes ?? []);
  useEffect(() => {
    zeon.onTipCounts((boxes) => setTipBoxes(boxes ?? []));
  }, []);

  // --- calculations -----------------------------------------------------------
  const sampleWater = r4(RECIPE_REF_UL - 3 - 4 - sampleDnaVol); // 3 - V at 10uL ref
  const scale = volPerWell / RECIPE_REF_UL;
  const perRxn: Record<Cond, { name: string; ref: number; preloaded?: boolean }[]> = {
    pos: [
      { name: "Extract", ref: 3 }, { name: "Buffer", ref: 4 },
      { name: "Control DNA", ref: 0.2, preloaded: true }, { name: "Water", ref: 2.8 },
    ],
    neg: [{ name: "Extract", ref: 3 }, { name: "Buffer", ref: 4 }, { name: "Water", ref: 3 }],
    sample: [
      { name: "Extract", ref: 3 }, { name: "Buffer", ref: 4 },
      { name: "Sample DNA", ref: sampleDnaVol, preloaded: true }, { name: "Water", ref: sampleWater },
    ],
  };

  const holeFor = (reagent: string): string => {
    switch (reagent) {
      case "Extract": return holes.extract_hole;
      case "Buffer": return holes.buffer_hole;
      case "Water": return holes.water_hole;
      case "Control DNA": return holes.ctrl_dna_hole;
      case "Sample DNA": return holes.sample_dna_hole;
      default: return "";
    }
  };
  // Per-mix tube volume = wells × per-well + a fixed dead-volume overage (extraUl).
  const tubeVol = (c: Cond) => (counts[c] > 0 ? r4(counts[c] * volPerWell + Math.max(0, extraUl)) : 0);
  type Row = { cond: Cond; reagent: string; hole: string; perWell: number; total: number; nStrokes: number; sub: boolean; active: boolean };
  const rows: Row[] = [];
  let anySub = false;
  (["pos", "neg", "sample"] as Cond[]).forEach((c) => {
    const active = counts[c] > 0; // dimmed until at least one well is painted for this mix
    const tube = tubeVol(c);
    perRxn[c].forEach((r) => {
      if (!(r.ref > 0) || r.preloaded) return; // skip empty + pre-loaded DNA (robot doesn't pipette it)
      const perWell = r4(r.ref * scale);
      const total = active ? r4((r.ref / RECIPE_REF_UL) * tube) : 0; // composition fraction × tube volume
      const sub = active && total > 0 && total < MIN_UL;
      if (sub) anySub = true;
      rows.push({ cond: c, reagent: r.name, hole: holeFor(r.name), perWell, total, nStrokes: active ? strokes(total) : 0, sub, active });
    });
  });

  // --- total amount of each reagent needed across the whole run (incl. overage) ---
  const REAGENT_ORDER = ["Extract", "Buffer", "Control DNA", "Sample DNA", "Water"];
  const reagentTotals: Record<string, number> = {};
  (["pos", "neg", "sample"] as Cond[]).forEach((c) => {
    if (counts[c] <= 0) return;
    const tube = tubeVol(c);
    perRxn[c].forEach((r) => {
      if (!(r.ref > 0) || r.preloaded) return; // DNA is pre-loaded in the tube, not from a source hole
      reagentTotals[r.name] = r4((reagentTotals[r.name] || 0) + (r.ref / RECIPE_REF_UL) * tube);
    });
  });
  const grandTotal = r4(Object.values(reagentTotals).reduce((a, b) => a + b, 0));

  // --- DNA to PRE-LOAD into each mix tube (operator does this by hand pre-run) ---
  const mmHole = (c: Cond) => (c === "pos" ? holes.pos_mm_hole : c === "neg" ? holes.neg_mm_hole : holes.sample_mm_hole);
  const preloads: { cond: Cond; name: string; hole: string; perWell: number; total: number }[] = [];
  (["pos", "neg", "sample"] as Cond[]).forEach((c) => {
    if (counts[c] <= 0) return;
    const tube = tubeVol(c);
    perRxn[c].forEach((r) => {
      if (!r.preloaded || !(r.ref > 0)) return;
      preloads.push({ cond: c, name: r.name, hole: mmHole(c), perWell: r4(r.ref * scale), total: r4((r.ref / RECIPE_REF_UL) * tube) });
    });
  });

  // --- estimated tip / aspirate usage across the whole run --------------------
  // A fresh tip is used per stroke; mixing uses 1 tip + MIX_CYCLES strokes per mix.
  const MIX_CYCLES = 5; // matches cfps_make_mastermix default
  let totalTips = 0;
  let totalStrokes = 0; // each stroke = 1 aspirate + 1 dispense
  // Tips come from a different rack per pipette, so track demand separately —
  // it's the per-rack count that can run out (checked against live box counts).
  const tipsBy = { small: 0, large: 0 };
  const addTips = (vol: number, n: number) => {
    tipsBy[pipetteFor(vol) === PIPETTES.small ? "small" : "large"] += n;
    totalTips += n;
  };
  (["pos", "neg", "sample"] as Cond[]).forEach((c) => {
    const n = counts[c];
    if (n <= 0) return;
    const tube = tubeVol(c);
    let lastVol = 0;
    perRxn[c].forEach((r) => {
      if (!(r.ref > 0) || r.preloaded) return; // DNA is pre-loaded, robot doesn't pipette it
      const vol = r4((r.ref / RECIPE_REF_UL) * tube);
      const s = strokes(vol);
      addTips(vol, s);
      totalStrokes += s;
      lastVol = vol;
    });
    addTips(lastVol, 1);                     // mix reuses whichever pipette ended up in hand
    totalStrokes += MIX_CYCLES;              // aspirate/dispense cycles while mixing
    const ds = strokes(volPerWell) * n;      // dispense: strokes/well × wells
    addTips(volPerWell, ds);
    totalStrokes += ds;
  });
  // Live tips available per rack type (a pipette rolls to the next same-type box
  // when one empties, so sum `remaining` across all boxes of that type).
  const availBy = {
    small: tipBoxes.filter((b) => b.type !== "tipbox_120ul" && b.type.startsWith("tipbox")).reduce((s, b) => s + (b.remaining || 0), 0),
    large: tipBoxes.filter((b) => b.type === "tipbox_120ul").reduce((s, b) => s + (b.remaining || 0), 0),
  };
  // Flag a shortfall only for a rack we actually have live counts for — no false
  // alarm before the host pushes tip data.
  const shortBy = {
    small: availBy.small > 0 && tipsBy.small > availBy.small,
    large: availBy.large > 0 && tipsBy.large > availBy.large,
  };
  const overTips = shortBy.small || shortBy.large;

  // --- per-well destination contents + column totals (dispensed, excl. overage) ---
  const plateWells = sortWells(Object.keys(assign));
  const wellRow = (c: Cond) => ({
    extract: r4(3 * scale),
    buffer: r4(4 * scale),
    ctrlDna: r4((c === "pos" ? 0.2 : 0) * scale),
    sampleDna: r4((c === "sample" ? sampleDnaVol : 0) * scale),
    water: r4((c === "pos" ? 2.8 : c === "neg" ? 3 : sampleWater) * scale),
    total: r4(volPerWell),
  });
  const plateTotals = plateWells.reduce(
    (acc, w) => {
      const b = wellRow(assign[w]);
      (Object.keys(acc) as (keyof typeof acc)[]).forEach((k) => (acc[k] = r4(acc[k] + b[k])));
      return acc;
    },
    { extract: 0, buffer: 0, ctrlDna: 0, sampleDna: 0, water: 0, total: 0 },
  );

  // --- validation -------------------------------------------------------------
  function usedHoles(): [string, string][] {
    const used: [string, string][] = [
      ["Extract", holes.extract_hole], ["Buffer", holes.buffer_hole], ["Water", holes.water_hole],
    ];
    if (counts.pos > 0) used.push(["Pos mix tube", holes.pos_mm_hole]);
    if (counts.neg > 0) used.push(["Neg mix tube", holes.neg_mm_hole]);
    if (counts.sample > 0) used.push(["Sample mix tube", holes.sample_mm_hole]);
    return used;
  }
  function validate(): string[] {
    const e: string[] = [];
    if (!pipette || !tipbox || !reagentBlock || !reactionPlate) e.push("Select the pipette, tip box, cold block, and destination plate.");
    if (counts.pos + counts.neg + counts.sample === 0) e.push("Assign at least one well on the plate map.");
    if (counts.sample > 0 && sampleWater < 0) e.push(`Sample DNA volume (${sampleDnaVol} uL) exceeds the 6 uL non-extract/buffer budget; water would be negative.`);
    if (!(volPerWell > 0)) e.push("Per-well volume must be positive.");
    const seen: Record<string, string> = {};
    usedHoles().forEach(([who, hole]) => {
      if (seen[hole]) e.push(`Hole ${hole} is assigned to both ${seen[hole]} and ${who} — each needs its own hole.`);
      else seen[hole] = who;
    });
    return e;
  }

  function run() {
    const e = validate();
    setErrors(e);
    if (e.length) return;
    zeon.submit({
      pipette, tipbox, reagent_block: reagentBlock, reaction_plate: reactionPlate,
      ...holes,
      vol_per_well: volPerWell,
      extra_volume_ul: Math.max(0, extraUl),
      sample_dna_vol: sampleDnaVol,
      sample_water_vol: sampleWater,
      pos_n: counts.pos, neg_n: counts.neg, sample_n: counts.sample,
      pos_wells: wellsOf("pos").join(","),
      neg_wells: wellsOf("neg").join(","),
      sample_wells: wellsOf("sample").join(","),
      platesealer, seal_holder: sealHolder, shaker, plate_home: plateHome,
      shaker_slot: shakerSlot,
      shaker_running: shakerRunning,
      seal_index: Math.max(1, Math.round(sealIndex || 1)),
      run_name: (runName || "").trim() || "cfps_run",
    });
  }

  const objSelect = (id: string, val: string, set: (v: string) => void, list: typeof zeon.worldObjects) => (
    <select id={id} style={S.field} value={val} onChange={(ev) => set(ev.target.value)}>
      {list.length === 0 && <option value="">(none in world)</option>}
      {list.map((o) => { const n = objName(o); return <option key={o.uuid} value={n}>{n}</option>; })}
    </select>
  );
  const holeSelect = (k: keyof typeof holes) => (
    <select style={S.field} value={holes[k]} onChange={(e) => setHole(k, e.target.value)}>
      {HOLES.map((h) => <option key={h} value={h}>{h}</option>)}
    </select>
  );

  return (
    <div style={S.page}>
      <div style={S.eyebrow}>
        <span style={{ width: 7, height: 7, borderRadius: 7, background: GREEN, display: "inline-block" }} />
        OpenCFPS · SepiaBio — Part 1 of 3
      </div>
      <h1 style={S.h1}>CFPS Workflow</h1>
      <p style={S.sub}>
        Make the CFPS enzyme plate end to end: the robot builds one master-mix tube per condition
        (Extract + Buffer + Water), aliquots into the wells you paint below, then seals the plate and loads it into the
        shaker to incubate. You pre-load the DNA by hand first — see <strong>Bench prep</strong> below for exactly what
        goes in each tube.
      </p>
      <hr style={S.rule} />

      <Info title="How this workflow works" tag="Part 1 of 3">
        <p style={S.p2}>
          This is <strong>Part 1 of the TEM-1 inhibitor screen: making the enzyme</strong> by cell-free protein
          synthesis (CFPS). It takes you from loaded tubes to a <em>sealed, shaking</em> plate, ready to incubate.
        </p>
        <p style={S.p2}>The robot runs these steps in order:</p>
        <ol style={S.ol}>
          <li style={S.li}><strong>Log the plate map</strong> — prints which wells are Positive / Negative / Sample to the run log.</li>
          <li style={S.li}><strong>Pick up the pipette</strong> off its stand.</li>
          <li style={S.li}><strong>Build three master-mix tubes</strong> — one each for the positive control, negative control, and sample. The robot pipettes Extract&nbsp;+&nbsp;Buffer&nbsp;+&nbsp;Water into each tube and mixes it. (You pre-load the DNA by hand — see <em>Bench prep</em>.)</li>
          <li style={S.li}><strong>Aliquot each mix</strong> into its painted wells on the flat-bottom plate.</li>
          <li style={S.li}><strong>Return the pipette</strong> to its stand.</li>
          <li style={S.li}><strong>Seal the plate</strong> on the PlateMax — grab it, load it in, apply a gas-permeable seal, and press seal — then set it back down.</li>
          <li style={S.li}><strong>Load it into the shaker</strong> and start shaking to incubate the expression reaction.</li>
        </ol>
        <p style={S.p2}>
          <strong>Why a master mix?</strong> Each condition is mixed once in a single tube, then split across its
          wells — so every replicate of a condition is identical and you pipette far fewer times. Each transfer picks
          its own pipette by volume — under 10&nbsp;µL the 10&nbsp;µL pipette, otherwise the 120&nbsp;µL one — swapping
          on the stand as needed, and anything above that pipette's maximum is drawn in several strokes automatically.
        </p>
        <p style={S.p2}>
          <strong>What comes next?</strong> Once this plate finishes incubating, Part&nbsp;2 reads sfGFP fluorescence to
          confirm the enzyme was actually made (the go / no-go gate), and Part&nbsp;3 runs the nitrocefin activity
          screen to measure inhibition.
        </p>
      </Info>

      <Info title="Assumptions & deck setup" tag="Read before running">
        <p style={S.p2}>This workflow assumes the following. Check each one before you run:</p>
        <ul style={S.ul}>
          <li style={S.li}>
            <strong>DNA is pre-loaded.</strong> Both the sample (plasmid) DNA and the positive-control DNA are added
            <em> by hand</em> into their microcentrifuge tubes <em>before</em> the run — and those tubes are the
            master-mix tubes. The robot only adds Extract, Buffer, and Water to them. The DNA volumes are below the
            on-deck pipetting minimum ({MIN_UL}&nbsp;µL), so the robot can't dispense them; the amounts to pre-load are
            listed under <em>Bench prep</em> below.
          </li>
          <li style={S.li}>
            <strong>Source plates 1, 2 and 3 are all compounds.</strong> The compound source plates
            (<span style={S.code}>wellplate_pcr_parts_1</span>…<span style={S.code}>_3</span>) hold the library compounds.
            They're used by the Part&nbsp;3 screen, not by this enzyme build.
          </li>
          <li style={S.li}>
            <strong>Everything is built on one flat-bottom plate.</strong> All reactions are assembled on the single
            96-well flat-bottom plate (<span style={S.code}>wellplate_96_flatbottom</span>).
          </li>
          <li style={S.li}>
            <strong>Seal goes shiny side up.</strong> Load the gas-permeable seal <strong>shiny side up</strong> in the
            reinforced plate stand (<span style={S.code}>seal_holder_stacked_reinforced</span>) so the robot can pick it
            at the end of the run. The gas-permeable seal lets the shaking expression step breathe.
          </li>
        </ul>
      </Info>

      <Info title="The science — TEM-1 β-lactamase inhibitor screen" tag="New here? Start here">
        <h4 style={S.h4}>Why this matters</h4>
        <p style={S.p2}>
          Antimicrobial resistance — bacteria surviving the drugs meant to kill them — is rising, and the world isn't
          ready for it.
        </p>
        <div style={S.quote}>
          "Approximately 1 in 6 laboratory-confirmed bacterial infections worldwide were resistant to antibiotics in
          2023." — World Health Organization
        </div>
        <p style={S.p2}>
          <strong>TEM-1</strong> is the archetypal resistance enzyme. Bacteria use it to shred penicillins before the
          drug can act — a big reason many antibiotics stopped working. Shut TEM-1 down and a "dead" antibiotic can get
          its teeth back, which is exactly what clinical inhibitors do.
        </p>

        <h4 style={S.h4}>The scientific question</h4>
        <p style={S.p2}>
          Which compounds meaningfully reduce TEM-1 activity, and what dose-response patterns do they show?
        </p>

        <h4 style={S.h4}>The three workflows</h4>
        <ol style={S.ol}>
          <li style={S.li}><strong>Make the enzyme (this workflow).</strong> Cell-free synthesis of TEM-1.</li>
          <li style={S.li}><strong>Confirm it.</strong> Read sfGFP fluorescence to check the enzyme was actually made — a go / no-go gate before you spend an assay on it.</li>
          <li style={S.li}><strong>Screen it.</strong> Build the assay plate, add compounds and nitrocefin, and read the reaction kinetically to measure inhibition.</li>
        </ol>

        <h4 style={S.h4}>Cell-free protein synthesis (CFPS)</h4>
        <p style={S.p2}>
          CFPS makes protein in a tube — no living cells. A cell extract supplies the transcription and translation
          machinery; you add a DNA template and the reaction reads it into protein in a few hours. (The kit protocol
          says ~6&nbsp;h, but green signal has appeared as early as ~30&nbsp;min.)
        </p>

        <h4 style={S.h4}>Reading out expression — sfGFP</h4>
        <p style={S.p2}>
          TEM-1 is expressed <em>fused</em> to superfolder GFP (sfGFP), so green fluorescence tells you protein was
          actually made. That green signal is the go / no-go gate in Part&nbsp;2.
        </p>

        <h4 style={S.h4}>Reading out activity — nitrocefin (Part 3)</h4>
        <p style={S.p2}>
          Nitrocefin is a chromogenic substrate: intact it's yellow, and when TEM-1 cleaves it, it turns red (read at
          A490). The <strong>initial slope of A490 vs. time is the enzyme's velocity</strong> — inhibit the enzyme and
          the slope drops.
        </p>

        <h4 style={S.h4}>The three conditions on this plate</h4>
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.thl}>Condition</th>
              <th style={S.thl}>Template (DNA)</th>
              <th style={S.thl}>What it tells you</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td style={{ ...S.tdl, color: COND_META.pos.color, fontWeight: 700 }}>Positive control</td>
              <td style={S.tdl}>~2450&nbsp;bp plasmid expressing sfGFP only; carries chloramphenicol resistance; supplied at 200&nbsp;nM (≈323&nbsp;ng/µL).</td>
              <td style={S.tdl}>The CFPS reaction works — you get green fluorescence, but <em>no</em> β-lactamase activity.</td>
            </tr>
            <tr>
              <td style={{ ...S.tdl, color: COND_META.sample.color, fontWeight: 700 }}>Sample</td>
              <td style={S.tdl}>The same vector with a cDNA insert encoding an <strong>sfGFP–β-lactamase (TEM-1) fusion</strong>, made by conventional cloning.</td>
              <td style={S.tdl}>The actual enzyme you screen against — green <em>and</em> β-lactamase active.</td>
            </tr>
            <tr>
              <td style={{ ...S.tdl, color: COND_META.neg.color, fontWeight: 700 }}>Negative control</td>
              <td style={S.tdl}>No template (no DNA).</td>
              <td style={S.tdl}>Background — confirms the signal needs DNA and isn't from the extract alone.</td>
            </tr>
          </tbody>
        </table>
        <p style={S.sub}>
          The positive control and sample templates share the same backbone; the sample just adds the β-lactamase
          coding sequence to the GFP reporter. That's why both glow green, but only the sample can chew through
          nitrocefin in Part&nbsp;3.
        </p>
      </Info>

      <WorkspaceMap />

      <h2 style={S.h2}>Deck</h2>
      <div style={S.grid2}>
        <div><label style={S.label}>Cold block (reagents + mixes)</label>{objSelect("blk", reagentBlock, setReagentBlock, blockP.list)}</div>
        <div><label style={S.label}>Destination plate</label>{objSelect("plt", reactionPlate, setReactionPlate, plateP.list)}</div>
        <div><label style={S.label}>Pipette</label>{objSelect("pip", pipette, setPipette, pipetteP.list)}</div>
      </div>

      {/* Tips are auto-selected by the robot (by type), so there's no tip-box picker.
          This read-only panel shows what's loaded and how many tips remain per box. */}
      <div style={{ ...S.card, ...(overTips ? { borderColor: "#fecaca", background: "#fef2f2" } : {}) }}>
        <div style={{ ...S.label, margin: "0 0 8px" }}>Tips on deck</div>
        {tipBoxes.length === 0 ? (
          <p style={{ ...S.sub, margin: 0 }}>Live tip counts not available yet.</p>
        ) : (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 18px" }}>
            {tipBoxes.map((b) => {
              const kind = b.type === "tipbox_120ul" ? "large" : "small";
              return (
                <div key={b.uuid} style={{ fontSize: 13 }}>
                  <span style={{ fontWeight: 600 }}>{b.name}</span>{b.active ? " ●" : ""}{" "}
                  <span style={shortBy[kind] ? S.flag : { fontFamily: MONO, color: MUTE }}>{b.remaining}/{b.capacity}</span>
                  <span style={{ color: FAINT, fontSize: 12 }}> {b.type === "tipbox_120ul" ? "120 µL" : "10 µL"}</span>
                </div>
              );
            })}
          </div>
        )}
        <p style={{ ...S.sub, margin: "8px 0 0" }}>● = rack in use. The robot picks the tip box by type and rolls to the next same-type box when one empties.</p>
      </div>

      <Info title="Cold-block hole assignments" tag="Defaults usually fine">
        <p style={S.p2}>
          Which cold-block hole holds each reagent and each master-mix tube. The defaults (hole_1…hole_8) match the
          standard cold block — only change these if your block is loaded differently.
        </p>
        <h4 style={S.h4}>Reagent holes (robot pipettes these)</h4>
        <div style={S.grid2}>
          <div><label style={S.label}>Extract (3.33X)</label>{holeSelect("extract_hole")}</div>
          <div><label style={S.label}>Buffer (2.5X)</label>{holeSelect("buffer_hole")}</div>
          <div><label style={S.label}>Water / additives</label>{holeSelect("water_hole")}</div>
        </div>
        <p style={S.sub}>
          Control DNA and Sample DNA are <strong>pre-loaded into the mix tubes by hand</strong> (too small to pipette
          on-deck), so they need no source holes — the amounts are shown under <em>Bench prep</em>.
        </p>
        <h4 style={S.h4}>Master-mix tube holes</h4>
        <div style={S.grid2}>
          <div><label style={S.label}>Positive-control mix</label>{holeSelect("pos_mm_hole")}</div>
          <div><label style={S.label}>Negative-control mix</label>{holeSelect("neg_mm_hole")}</div>
          <div><label style={S.label}>Sample mix</label>{holeSelect("sample_mm_hole")}</div>
        </div>
      </Info>

      <h2 style={S.h2}>Run parameters</h2>
      <div style={S.grid2}>
        <div>
          <label style={S.label}>Volume per well (uL) — 15–30 recommended</label>
          <input type="number" min={1} step={1} style={S.field} value={volPerWell}
                 onChange={(e) => setVolPerWell(parseFloat(e.target.value))} />
        </div>
        <div>
          <label style={S.label}>Extra volume per mix (µL dead volume)</label>
          <input type="number" min={0} step={1} style={S.field} value={extraUl}
                 onChange={(e) => setExtraUl(parseFloat(e.target.value || "0"))} />
        </div>
        <div>
          <label style={S.label}>Sample DNA stock (nM)</label>
          <input type="number" min={1} step={1} style={S.field} value={dnaStock}
                 onChange={(e) => setDnaStock(parseFloat(e.target.value || "0"))} />
        </div>
        <div>
          <label style={S.label}>Sample DNA final (nM) — 4 plasmid / 8 linear</label>
          <input type="number" min={0} step={0.5} style={S.field} value={dnaFinal}
                 onChange={(e) => setDnaFinal(parseFloat(e.target.value || "0"))} />
        </div>
      </div>
      <p style={S.sub}>
        Sample DNA works out to <strong>{sampleDnaVol} µL per 10 µL reaction</strong> ({dnaFinal} nM final from a{" "}
        {dnaStock} nM stock) — the same tiny order as the 0.2 µL Control DNA, which is why both are pre-loaded by hand.
      </p>

      <h2 style={S.h2}>Plate map — paint wells by condition</h2>
      <div style={S.paintRow}>
        {(["pos", "neg", "sample"] as Cond[]).map((c) => (
          <button key={c} type="button" onClick={() => setPaint(c)}
                  style={{ ...S.paintBtn, background: paint === c ? COND_META[c].color : "#fff", color: paint === c ? "#fff" : COND_META[c].color, borderColor: COND_META[c].color }}>
            {COND_META[c].label} ({counts[c]})
          </button>
        ))}
        <button type="button" onClick={() => setPaint("erase")}
                style={{ ...S.paintBtn, background: paint === "erase" ? INK : "#fff", color: paint === "erase" ? "#fff" : INK }}>
          Erase
        </button>
      </div>
      <div style={S.plate}>
        <div />
        {COLS.map((c) => <div key={c} style={S.hdr}>{c}</div>)}
        {ROWS.map((r) => (
          <React.Fragment key={r}>
            <div style={S.hdr}>{r}</div>
            {COLS.map((c) => {
              const w = `${r}${c}`;
              const cond = assign[w];
              return (
                <button key={w} type="button" title={w} onClick={() => paintWell(w)}
                        style={{ ...S.cell, background: cond ? COND_META[cond].color : "#fff", color: cond ? "#fff" : FAINT }}>
                  {cond ? COND_META[cond].short : ""}
                </button>
              );
            })}
          </React.Fragment>
        ))}
      </div>

      <Info title="Sealing, shaking & run output" tag="Defaults usually fine">
        <p style={S.p2}>
          After pipetting, the plate is sealed on the PlateMax, dropped back home, then loaded into the
          shaker and started for incubation. Pick the deck hardware and name this run's saved output folder.
        </p>
        <div style={S.grid2}>
          <div>
            <label style={S.label} htmlFor="platesealer">Plate sealer</label>
            {objSelect("platesealer", platesealer, setPlatesealer, sealerP.list)}
          </div>
          <div>
            <label style={S.label} htmlFor="seal_holder">Seal holder</label>
            {objSelect("seal_holder", sealHolder, setSealHolder, sealHolderP.list)}
          </div>
          <div>
            <label style={S.label} htmlFor="shaker">Shaker</label>
            {objSelect("shaker", shaker, setShaker, shakerP.list)}
          </div>
          <div>
            <label style={S.label} htmlFor="plate_home">Plate home (drop target)</label>
            {objSelect("plate_home", plateHome, setPlateHome, plateHomeP.list)}
          </div>
          <div>
            <label style={S.label} htmlFor="shaker_slot">Shaker slot</label>
            <input id="shaker_slot" style={S.field} value={shakerSlot}
                   onChange={(e) => setShakerSlot(e.target.value)} placeholder="slot_1" />
          </div>
          <div>
            <label style={S.label} htmlFor="shaker_running">Is the shaker running right now?</label>
            <select id="shaker_running" style={S.field} value={shakerRunning}
                    onChange={(e) => setShakerRunning(e.target.value)}>
              <option value="no">No — it is stopped</option>
              <option value="yes">Yes — it is already shaking</option>
            </select>
            <div style={{ ...S.sub, fontSize: 12, margin: "5px 0 0" }}>
              The shaker has no sensor, so the robot only knows what it was last told. Check the machine — if this is
              wrong, the run presses its button at the wrong times.
            </div>
          </div>
          <div>
            <label style={S.label} htmlFor="seal_index">Seal index</label>
            <input id="seal_index" type="number" min={1} step={1} style={S.field} value={sealIndex}
                   onChange={(e) => setSealIndex(Math.max(1, Math.round(Number(e.target.value) || 1)))} />
          </div>
        </div>
        <label style={S.label} htmlFor="run_name">Run name (output folder)</label>
        <input id="run_name" style={S.field} value={runName}
               onChange={(e) => setRunName(e.target.value)} placeholder="cfps_run" />
      </Info>

      <h2 style={S.h2}>Bench prep — fill these tubes before you run</h2>
      <p style={S.sub}>
        Load each tube in the cold block by hand, then press Run. Every amount already includes the {extraUl} µL
        per-tube dead-volume overage, so each well — and the little left over in every tube — stays at the right
        concentration.
      </p>
      {grandTotal <= 0 ? (
        <p style={S.sub}>Paint at least one well on the plate map above to see your prep amounts.</p>
      ) : (
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.thl}>Tube</th>
              <th style={S.thl}>Hole</th>
              <th style={S.thl}>What you add</th>
              <th style={S.th}>Amount (µL)</th>
            </tr>
          </thead>
          <tbody>
            <tr><td style={S.groupRow} colSpan={4}>Reagent source tubes — the robot draws from these</td></tr>
            {REAGENT_ORDER.filter((nm) => reagentTotals[nm] > 0).map((nm) => (
              <tr key={nm}>
                <td style={S.tdl}>{nm}</td>
                <td style={S.tdl}>{holeFor(nm)}</td>
                <td style={S.tdl}>{nm} stock</td>
                <td style={{ ...S.td, fontWeight: 700 }}>{reagentTotals[nm]}</td>
              </tr>
            ))}
            <tr><td style={S.groupRow} colSpan={4}>Master-mix tubes — you pre-load DNA; the robot then adds Extract + Buffer + Water and mixes</td></tr>
            {preloads.map((p, i) => (
              <tr key={i}>
                <td style={{ ...S.tdl, color: COND_META[p.cond].color, fontWeight: 700 }}>{COND_META[p.cond].label} mix</td>
                <td style={S.tdl}>{p.hole}</td>
                <td style={S.tdl}>{p.name}</td>
                <td style={{ ...S.td, fontWeight: 700 }}>{p.total}</td>
              </tr>
            ))}
            {counts.neg > 0 && (
              <tr>
                <td style={{ ...S.tdl, color: COND_META.neg.color, fontWeight: 700 }}>{COND_META.neg.label} mix</td>
                <td style={S.tdl}>{holes.neg_mm_hole}</td>
                <td style={S.tdl}>Nothing — leave the tube empty (no DNA)</td>
                <td style={S.td}>—</td>
              </tr>
            )}
            {preloads.length === 0 && counts.neg === 0 && (
              <tr><td style={S.tdl} colSpan={4}>No mix tubes need pre-loading for the painted wells.</td></tr>
            )}
          </tbody>
          <tfoot>
            <tr>
              <td style={{ ...S.tdl, fontWeight: 700 }} colSpan={3}>Total reagent across the source tubes</td>
              <td style={{ ...S.td, fontWeight: 700 }}>{grandTotal}</td>
            </tr>
          </tfoot>
        </table>
      )}
      {counts.sample > 0 && sampleDnaVol > 0 && (
        <p style={S.sub}>
          <strong>Your sample-DNA question:</strong> you pre-load{" "}
          <strong>{(preloads.find((p) => p.cond === "sample") || { total: 0 }).total} µL</strong> of sample DNA into the
          sample mix tube ({holes.sample_mm_hole}). That is {sampleDnaVol} µL per 10 µL reaction scaled up to the whole
          tube — {counts.sample} well{counts.sample !== 1 ? "s" : ""} × {volPerWell} µL <em>plus</em> the {extraUl} µL
          overage ({tubeVol("sample")} µL total). So yes: the DNA goes into the master mix, and the overage carries its
          share of DNA too, so every well pours at the same concentration.
        </p>
      )}

      <h2 style={S.h2}>The recipe — what's in one reaction</h2>
      <p style={S.sub}>
        The OpenCFPS™ (SepiaBio) kit recipe, per 10 µL reference reaction. Your run keeps these ratios and scales them
        to {volPerWell} µL per well.
      </p>
      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.thl}>Reagent</th>
            <th style={S.th}>Pos ctrl</th>
            <th style={S.th}>Neg ctrl</th>
            <th style={S.th}>Sample</th>
          </tr>
        </thead>
        <tbody>
          <tr><td style={S.tdl}>Extract (3.33X)</td><td style={S.td}>3</td><td style={S.td}>3</td><td style={S.td}>3</td></tr>
          <tr><td style={S.tdl}>Buffer (2.5X)</td><td style={S.td}>4</td><td style={S.td}>4</td><td style={S.td}>4</td></tr>
          <tr><td style={S.tdl}>Control DNA (200 nM)</td><td style={S.td}>0.2</td><td style={S.td}>—</td><td style={S.td}>—</td></tr>
          <tr><td style={S.tdl}>Sample DNA (plasmid)</td><td style={S.td}>—</td><td style={S.td}>—</td><td style={S.td}>{sampleDnaVol}</td></tr>
          <tr><td style={S.tdl}>Additives / Water</td><td style={S.td}>2.8</td><td style={S.td}>3</td><td style={S.td}>{r4(sampleWater)}</td></tr>
          <tr>
            <td style={{ ...S.tdl, fontWeight: 700 }}>Total</td>
            <td style={{ ...S.td, fontWeight: 700 }}>10</td>
            <td style={{ ...S.td, fontWeight: 700 }}>10</td>
            <td style={{ ...S.td, fontWeight: 700 }}>{r4(3 + 4 + sampleDnaVol + sampleWater)}</td>
          </tr>
        </tbody>
      </table>
      <ul style={S.ul}>
        <li style={S.li}><strong>Extract (3.33×)</strong> — the cell-free machinery that reads DNA into protein.</li>
        <li style={S.li}><strong>Buffer (2.5×)</strong> — energy and salts that keep the reaction running.</li>
        <li style={S.li}><strong>DNA template</strong> — pre-loaded by hand: Control DNA for the positive control, your plasmid for the sample, none for the negative.</li>
        <li style={S.li}><strong>Additives / Water</strong> — brings each reaction up to volume.</li>
      </ul>

      <Info title="Robot & per-well detail" tag={anySub ? "⚠ check volumes" : overTips ? "⚠ tip box" : "Optional"}>
        <h4 style={S.h4}>What the robot pipettes into each mix tube</h4>
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.thl}>Mix</th><th style={S.thl}>Reagent</th><th style={S.thl}>Hole</th>
              <th style={S.th}>µL/well</th>
              <th style={S.th}>total µL</th><th style={S.th}>strokes</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} style={r.active ? undefined : { opacity: 0.4 }}>
                <td style={{ ...S.tdl, color: COND_META[r.cond].color, fontWeight: 700 }}>{COND_META[r.cond].short}</td>
                <td style={S.tdl}>{r.reagent}</td>
                <td style={S.tdl}>{r.hole}</td>
                <td style={S.td}>{r.perWell}</td>
                <td style={{ ...S.td, ...(r.sub ? S.flag : {}) }}>{r.active ? `${r.total}${r.sub ? " ⚠" : ""}` : "—"}</td>
                <td style={S.td}>{r.active ? r.nStrokes : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p style={S.sub}>
          Tube volume per mix = wells × per-well + {extraUl} µL dead volume. Each reagent is drawn in ⌈total ÷ 10 µL⌉
          strokes (10 µL pipette max). Dimmed rows are mixes with no wells painted yet.
        </p>
        <div style={{ ...S.card, display: "flex", justifyContent: "space-between", alignItems: "center", ...(overTips ? { borderColor: "#fecaca", background: "#fef2f2" } : {}) }}>
          <div style={{ fontSize: 13 }}>
            <strong>Estimated usage:</strong> {totalTips} tips ({tipsBy.small} × 10&nbsp;µL, {tipsBy.large} × 120&nbsp;µL) · {totalStrokes} aspirate/dispense strokes
          </div>
          {overTips && (
            <div style={S.flag}>
              ⚠ not enough tips loaded — {shortBy.small
                ? `10 µL: need ${tipsBy.small}, ${availBy.small} left`
                : `120 µL: need ${tipsBy.large}, ${availBy.large} left`}
            </div>
          )}
        </div>

        <h4 style={S.h4}>Per-well contents (dispensed, excludes overage)</h4>
        {Object.keys(assign).length === 0 ? (
          <p style={S.sub}>Paint wells on the plate map to see each well's contents.</p>
        ) : (
          <table style={S.table}>
            <thead>
              <tr>
                <th style={S.thl}>Well</th><th style={S.thl}>Mix</th>
                <th style={S.th}>Extract</th><th style={S.th}>Buffer</th>
                <th style={S.th}>Ctrl DNA</th><th style={S.th}>Sample DNA</th>
                <th style={S.th}>Water</th><th style={S.th}>Total µL</th>
              </tr>
            </thead>
            <tbody>
              {sortWells(Object.keys(assign)).map((w) => {
                const c = assign[w];
                const s = scale;
                const ex = r4(3 * s);
                const bf = r4(4 * s);
                const cd = r4((c === "pos" ? 0.2 : 0) * s);
                const sd = r4((c === "sample" ? sampleDnaVol : 0) * s);
                const wt = r4((c === "pos" ? 2.8 : c === "neg" ? 3 : sampleWater) * s);
                const cell = (v: number) => (v > 0 ? v : "—");
                return (
                  <tr key={w}>
                    <td style={S.tdl}>{w}</td>
                    <td style={{ ...S.tdl, color: COND_META[c].color, fontWeight: 700 }}>{COND_META[c].short}</td>
                    <td style={S.td}>{cell(ex)}</td>
                    <td style={S.td}>{cell(bf)}</td>
                    <td style={S.td}>{cell(cd)}</td>
                    <td style={S.td}>{cell(sd)}</td>
                    <td style={S.td}>{cell(wt)}</td>
                    <td style={{ ...S.td, fontWeight: 700 }}>{r4(volPerWell)}</td>
                  </tr>
                );
              })}
            </tbody>
            <tfoot>
              <tr>
                <td style={{ ...S.tdl, fontWeight: 700 }} colSpan={2}>Total dispensed ({plateWells.length} well{plateWells.length !== 1 ? "s" : ""})</td>
                <td style={{ ...S.td, fontWeight: 700 }}>{plateTotals.extract || "—"}</td>
                <td style={{ ...S.td, fontWeight: 700 }}>{plateTotals.buffer || "—"}</td>
                <td style={{ ...S.td, fontWeight: 700 }}>{plateTotals.ctrlDna || "—"}</td>
                <td style={{ ...S.td, fontWeight: 700 }}>{plateTotals.sampleDna || "—"}</td>
                <td style={{ ...S.td, fontWeight: 700 }}>{plateTotals.water || "—"}</td>
                <td style={{ ...S.td, fontWeight: 700 }}>{plateTotals.total || "—"}</td>
              </tr>
            </tfoot>
          </table>
        )}
      </Info>

      {anySub && (
        <div style={S.warn}>
          ⚠ One or more reagent volumes are below the {MIN_UL} uL pipette minimum (flagged above). Increase the
          well count, the extra reactions, or the per-well volume to lift them above {MIN_UL} uL.
        </div>
      )}

      {errors.length > 0 && (
        <div style={S.errorBox}>{errors.map((m, i) => <div key={i}>• {m}</div>)}</div>
      )}

      <button type="button" style={S.button} onClick={run}>
        Run — {counts.pos + counts.neg + counts.sample} well(s), {[counts.pos && "Pos", counts.neg && "Neg", counts.sample && "Sample"].filter(Boolean).join(" + ") || "none"}
      </button>
    </div>
  );
}
