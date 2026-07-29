// Canvas for the `cfps_inhibitor_dose` workflow (Part 3a of the TEM-1 screen).
//
// Sized to the purified-enzyme dose-response design in exp2_100ul_report.md: 5
// compound rows (A-E, 4 concentrations x 2 duplicate wells each, compound
// preplated by hand before this run) plus a vehicle-control row (F1-F4, 2
// duplicate pairs) -- 44 wells, one robot run. Compound, vehicle, and (later)
// nitrocefin are all manual, off-robot (see the report's "Pipetting workflow"
// section) -- the robot's only job here is enzyme, from a fresh per-row aliquot
// tube in a cold block. Each row keeps one tip for its whole span (the enzyme
// source and volume are constant across a row), and each duplicate pair shares a
// single aspirate: one draw of 2x the per-well volume, split into two equal
// dispenses, so the aliquot tube is only touched once per pair. The row/pair
// well layout is fixed by the plate map, not picked by clicking -- this canvas
// exposes it as an editable table (defaults match the report) plus a read-only
// preview of which wells the robot will touch.
//
// Sandboxed iframe contract: only `react` may be imported, no network/FS, all host
// communication via the injected `zeon.*` globals; `export default` the component.
// Object inputs submit the world-object NAME (never a UUID).
//
// height/overflow on S.page is a deliberate deviation from the canvas doc's "don't
// set your own scroll container" guidance — confirmed with Zeon as the right call
// for this workflow family, where the host's own auto-resize wasn't reaching every
// row. 100vh caps the canvas to its own iframe viewport so it scrolls internally no
// matter what height the host actually grants the iframe.

import React, { useEffect, useMemo, useState } from "react";

declare const zeon: {
  schema: { name: string; type: string; description?: string; defaultValue?: unknown; isArray?: boolean }[];
  worldObjects: { uuid: string; name: string; displayName?: string; meshType?: string }[];
  // NOT the workflow's declared defaults — these are previously *staged* values:
  // a sessionStorage draft, or the saved inputs of a live (running/paused) run,
  // replayed on every mount. The pipeline's planned round arrives via
  // `schema[].defaultValue` instead, so both are consulted below and the planned
  // round wins.
  defaults: Record<string, unknown>;
  submit: (values: Record<string, unknown>) => void;
  onValidationErrors: (cb: (errs: { path: string; message: string }[]) => void) => void;
  resetInputs?: () => void;
};

const COLS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
const ROW_LETTERS = ["A", "B", "C", "D", "E", "F", "G", "H"];

// Fixed row/pair shape from exp2_100ul_report.md's "Plate / well layout" — 5
// compound rows of 4 duplicate pairs, plus a vehicle-control row of 2 pairs.
// Wells are editable per-row (in case the physical plate differs) but default
// to exactly this table.
const ROW_DEFS = [
    { key: "row1", letter: "A", pairs: 4 },
    { key: "row2", letter: "B", pairs: 4 },
    { key: "row3", letter: "C", pairs: 4 },
    { key: "row4", letter: "D", pairs: 4 },
    { key: "row5", letter: "E", pairs: 4 },
    { key: "row6", letter: "F", pairs: 2 },
] as const;
const ROW_COLORS = ["#9D174D", "#B45309", "#3F6212", "#1D4ED8", "#7E22CE", "#0F766E"];

// Mirrors skills/utils.py PIPETTES — (min, max) draw volume in uL per pipette.
// Used only to warn client-side whether the combined (2x) aspirate fits in one
// draw; the authoritative limits still live in the skill layer.
const PIPETTE_LIMITS: Record<string, [number, number]> = {
  epipette_10ul: [0.5, 10.0],
  epipette_120ul: [10.0, 120.0],
};
const pipetteLimits = (name: string): [number, number] => {
  const key = Object.keys(PIPETTE_LIMITS).find((k) => name.toLowerCase().includes(k.replace("epipette_", "")));
  return PIPETTE_LIMITS[key || "epipette_120ul"] || PIPETTE_LIMITS.epipette_120ul;
};

const SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
const MONO = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace";
const INK = "#16231C", MUTE = "#5B6B62", FAINT = "#94A29A";
const LINE = "#E3E8E3", HAIR = "#EFF2EF", PAPER = "#FCFCFA";
const ACCENT = "#9D174D", ACCENT_SOFT = "#FBEAF1"; // same family accent as Part 3b (nitrocefin-red)

const S: Record<string, React.CSSProperties> = {
  page: { fontFamily: SANS, color: INK, background: PAPER, padding: "34px 26px 46px", maxWidth: 860, margin: "0 auto", fontSize: 14, lineHeight: 1.55, WebkitFontSmoothing: "antialiased", height: "100vh", boxSizing: "border-box", overflowY: "auto" },
  eyebrow: { fontFamily: MONO, fontSize: 11, fontWeight: 600, letterSpacing: 1.6, textTransform: "uppercase", color: MUTE, margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 },
  h1: { fontFamily: SANS, fontSize: 27, fontWeight: 800, letterSpacing: -0.7, lineHeight: 1.05, margin: "0 0 10px", color: INK },
  sub: { fontSize: 13.5, color: MUTE, margin: "0 0 4px", lineHeight: 1.6, maxWidth: "74ch" },
  rule: { height: 1, background: LINE, border: 0, margin: "22px 0 2px" },
  h2: { fontFamily: MONO, fontSize: 11, fontWeight: 700, margin: "36px 0 12px", paddingTop: 18, color: INK, textTransform: "uppercase", letterSpacing: 1.3, borderTop: `1px solid ${LINE}`, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 },
  smallBtn: { fontFamily: MONO, fontSize: 10.5, fontWeight: 700, color: ACCENT, background: "#fff", border: `1px solid ${LINE}`, borderRadius: 5, padding: "4px 9px", cursor: "pointer", textTransform: "uppercase", letterSpacing: 0.4, whiteSpace: "nowrap" },
  staleBox: { background: "#FDF6E3", border: "1px solid #E5D5A8", borderRadius: 8, padding: "11px 13px", marginTop: 12, fontSize: 12.5, color: "#6B5518", lineHeight: 1.5 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 16px" },
  grid4: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: "10px 16px" },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, fontWeight: 600, margin: "12px 0 5px", color: MUTE, textTransform: "uppercase", letterSpacing: 0.6 },
  field: { width: "100%", boxSizing: "border-box", padding: "9px 11px", fontFamily: SANS, fontSize: 13.5, border: `1px solid ${LINE}`, borderRadius: 7, background: "#fff", color: INK, outline: "none" },
  card: { border: `1px solid ${LINE}`, borderRadius: 8, padding: 14, marginTop: 12, background: "#fff" },
  plate: { display: "inline-grid", gridTemplateColumns: `20px repeat(12, 27px)`, gap: 4, userSelect: "none" },
  hdr: { fontFamily: MONO, fontSize: 9.5, color: FAINT, textAlign: "center", lineHeight: "27px" },
  cell: { width: 27, height: 27, borderRadius: 5, border: `1px solid ${LINE}`, fontFamily: MONO, fontSize: 9, color: "#fff", fontWeight: 700, padding: 0, display: "flex", alignItems: "center", justifyContent: "center" },
  table: { width: "100%", borderCollapse: "collapse", fontFamily: SANS, fontSize: 12.5, marginTop: 10 },
  th: { fontFamily: MONO, textAlign: "left", padding: "7px 8px", borderBottom: `1.5px solid ${INK}`, color: MUTE, fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  td: { fontFamily: SANS, textAlign: "left", padding: "6px 8px", borderBottom: `1px solid ${HAIR}` },
  numInput: { width: 80, boxSizing: "border-box", padding: "5px 7px", fontFamily: MONO, fontSize: 12.5, border: `1px solid ${LINE}`, borderRadius: 5, background: "#fff", color: INK },
  textInput: { width: 92, boxSizing: "border-box", padding: "5px 7px", fontFamily: MONO, fontSize: 12.5, border: `1px solid ${LINE}`, borderRadius: 5, background: "#fff", color: INK },
  wellInput: { width: 52, boxSizing: "border-box", padding: "5px 6px", fontFamily: MONO, fontSize: 12, border: `1px solid ${LINE}`, borderRadius: 5, background: "#fff", color: INK, textAlign: "center" as const },
  errorBox: { background: "#FBEEEB", border: "1px solid #E7C1B9", borderRadius: 8, padding: "11px 13px", marginTop: 14, fontSize: 13, color: "#8E2C1E", lineHeight: 1.5 },
  button: { width: "100%", marginTop: 24, padding: "14px 16px", fontFamily: SANS, fontSize: 14.5, fontWeight: 700, letterSpacing: 0.2, color: "#fff", background: ACCENT, border: "none", borderRadius: 8, cursor: "pointer" },
};

const objName = (o: { name?: string; displayName?: string; uuid: string }) => o.displayName || o.name || o.uuid;

const plannedValue = (k: string): unknown => zeon.schema?.find((s) => s.name === k)?.defaultValue;
const stagedValue = (k: string): unknown => zeon.defaults?.[k];
// Planned wins — see the note on `defaults` above.
const rawDefault = (k: string): unknown => {
  const p = plannedValue(k);
  if (p !== undefined && p !== null && p !== "") return p;
  return stagedValue(k);
};
type Source = "auto" | "planned" | "staged";
const pickBy = (source: Source) => {
  const get = source === "planned" ? plannedValue : source === "staged" ? stagedValue : rawDefault;
  return {
    s: (k: string, fb: string) => (typeof get(k) === "string" && get(k) !== "" ? (get(k) as string) : fb),
    n: (k: string, fb: number) => (typeof get(k) === "number" ? (get(k) as number) : fb),
  };
};
const strDefault = (k: string, fb: string) => pickBy("auto").s(k, fb);
const numDefault = (k: string, fb: number) => pickBy("auto").n(k, fb);

type PairWells = { wellA: string; wellB: string };
type RowState = { label: string; srcHole: string; tipIndex: number; pairs: PairWells[] };

const rowFrom = (source: Source, key: string, pairCount: number): RowState => {
  const { s, n } = pickBy(source);
  const pairs: PairWells[] = [];
  for (let p = 1; p <= pairCount; p++) {
    pairs.push({ wellA: s(`${key}_p${p}_well_a`, ""), wellB: s(`${key}_p${p}_well_b`, "") });
  }
  return {
    label: s(`${key}_label`, ""),
    srcHole: s(`${key}_src_hole`, ""),
    tipIndex: n(`${key}_tip_index`, 1),
    pairs,
  };
};
const allRowsFrom = (source: Source): Record<string, RowState> => {
  const out: Record<string, RowState> = {};
  ROW_DEFS.forEach((r) => { out[r.key] = rowFrom(source, r.key, r.pairs); });
  return out;
};

export default function CfpsInhibitorDoseScreen() {
  const pick = (match: (m: string) => boolean, dfltKey: string, fallback: string) => {
    const all = zeon.worldObjects;
    const hits = all.filter((o) => match((o.meshType || "").toLowerCase()));
    const list = hits.length ? hits : all;
    const d = strDefault(dfltKey, fallback);
    if (d && list.some((o) => objName(o) === d)) return { list, init: d };
    if (fallback && list.some((o) => objName(o) === fallback)) return { list, init: fallback };
    return { list, init: list[0] ? objName(list[0]) : "" };
  };
  const pipetteP = useMemo(() => pick((m) => (m.includes("epipette") || m.includes("pipette")) && !m.includes("stand") && !m.includes("holder"), "pipette", "epipette_120ul"), []);
  const tipboxP = useMemo(() => pick((m) => m.includes("tipbox") && !m.includes("holder"), "tipbox", "tipbox_120ul_1"), []);
  const plateP = useMemo(() => pick((m) => m.includes("wellplate") && !m.includes("coldblock") && !m.includes("holder") && !m.includes("shaker") && !m.includes("pcr"), "reaction_plate", "wellplate_96_flatbottom"), []);
  const blockP = useMemo(() => pick((m) => m.includes("coldblock"), "reagent_block", "coldblock_wellplate"), []);
  const sealerP = useMemo(() => pick((m) => m.includes("sealer"), "platesealer", "platesealer_platemax_1"), []);
  const sealHolderP = useMemo(() => pick((m) => m.includes("seal_holder") || (m.includes("seal") && m.includes("holder")), "seal_holder", "seal_holder_stacked_reinforced_1"), []);
  const shakerP = useMemo(() => pick((m) => m.includes("shaker") && !m.includes("holder"), "shaker", "wellplate_shaker_1"), []);
  const plateHomeP = useMemo(() => pick((m) => m.includes("holder") && m.includes("wellplate"), "plate_home", "wellplate_holder_tags"), []);

  const [pipette, setPipette] = useState(pipetteP.init);
  const [tipbox, setTipbox] = useState(tipboxP.init);
  const [reactionPlate, setReactionPlate] = useState(plateP.init);
  const [reagentBlock, setReagentBlock] = useState(blockP.init);
  const [enzymeVolUl, setEnzymeVolUl] = useState(numDefault("enzyme_vol_ul", 40.0));
  const [runName, setRunName] = useState(strDefault("run_name", "cfps_inhibitor_dose_run"));

  // Post-pipetting: seal the plate, then load it into the shaker/incubator (lid
  // closed) and stop — starting/monitoring the incubation is manual from there.
  const [platesealer, setPlatesealer] = useState(sealerP.init);
  const [sealHolder, setSealHolder] = useState(sealHolderP.init);
  const [shaker, setShaker] = useState(shakerP.init);
  const [plateHome, setPlateHome] = useState(plateHomeP.init);
  const [shakerSlot, setShakerSlot] = useState(strDefault("shaker_slot", "slot_1"));
  const [sealIndex, setSealIndex] = useState(numDefault("seal_index", 1));

  const [, pipetteMax] = useMemo(() => pipetteLimits(pipette), [pipette]);
  const totalVolUl = enzymeVolUl * 2;
  const overCapacity = totalVolUl > pipetteMax;

  const [rows, setRows] = useState<Record<string, RowState>>(() => allRowsFrom("auto"));

  const stagedDiffers = useMemo(() => {
    const planned = allRowsFrom("planned");
    const staged = allRowsFrom("staged");
    const stagedHasAny = Object.values(staged).some((r) => r.label || r.pairs.some((p) => p.wellA || p.wellB));
    if (!stagedHasAny) return false;
    return JSON.stringify(planned) !== JSON.stringify(staged);
  }, []);
  const loadFrom = (source: Source) => {
    const { s, n } = pickBy(source);
    setRows(allRowsFrom(source));
    setEnzymeVolUl(n("enzyme_vol_ul", 40.0));
    setRunName(s("run_name", "cfps_inhibitor_dose_run"));
    setShakerSlot(s("shaker_slot", "slot_1"));
    setSealIndex(n("seal_index", 1));
  };

  const updateRow = (key: string, patch: Partial<RowState>) =>
    setRows((rs) => ({ ...rs, [key]: { ...rs[key], ...patch } }));
  const updatePair = (key: string, idx: number, patch: Partial<PairWells>) =>
    setRows((rs) => ({
      ...rs,
      [key]: { ...rs[key], pairs: rs[key].pairs.map((p, i) => (i === idx ? { ...p, ...patch } : p)) },
    }));

  const [errors, setErrors] = useState<string[]>([]);
  useEffect(() => {
    zeon.onValidationErrors((errs) => setErrors(errs.map((e) => e.message)));
  }, []);

  function validate(): string[] {
    const e: string[] = [];
    if (!pipette || !tipbox || !reactionPlate || !reagentBlock) {
      e.push("Select the pipette, tip box, reaction plate, and reagent block (enzyme aliquots).");
    }
    if (!platesealer || !sealHolder || !plateHome || !shaker) {
      e.push("Select the plate sealer, seal holder, plate home, and shaker/incubator.");
    }
    if (!shakerSlot.trim()) e.push("Set the shaker slot anchor to load the plate into.");
    if (!(sealIndex >= 1)) e.push("Seal index must be at least 1.");
    if (!(enzymeVolUl > 0)) e.push("Enzyme volume per well must be positive.");
    if (overCapacity) {
      e.push(`Combined draw ${totalVolUl.toFixed(1)} uL (2 x ${enzymeVolUl} uL) exceeds ${pipette}'s ${pipetteMax} uL capacity — lower the enzyme volume or use a larger pipette.`);
    }
    ROW_DEFS.forEach((rd) => {
      const r = rows[rd.key];
      if (!r.srcHole.trim()) e.push(`Row ${rd.letter}: set the reagent_block hole holding its enzyme aliquot.`);
      r.pairs.forEach((p, i) => {
        if (!p.wellA.trim() || !p.wellB.trim()) e.push(`Row ${rd.letter} pair ${i + 1}: both duplicate wells are required.`);
      });
    });
    return e;
  }

  function run() {
    const e = validate();
    setErrors(e);
    if (e.length) return;

    const values: Record<string, unknown> = {
      pipette, tipbox, reaction_plate: reactionPlate, reagent_block: reagentBlock,
      enzyme_vol_ul: enzymeVolUl,
      enzyme_total_vol_ul: totalVolUl,
      platesealer, seal_holder: sealHolder, plate_home: plateHome, shaker,
      shaker_slot: shakerSlot.trim() || "slot_1",
      seal_index: Math.max(1, Math.round(sealIndex || 1)),
      run_name: (runName || "").trim() || "cfps_inhibitor_dose_run",
    };
    ROW_DEFS.forEach((rd, ri) => {
      const r = rows[rd.key];
      values[`${rd.key}_label`] = r.label.trim();
      values[`${rd.key}_src_hole`] = r.srcHole.trim();
      values[`${rd.key}_tip_index`] = ri + 1;
      r.pairs.forEach((p, i) => {
        values[`${rd.key}_p${i + 1}_well_a`] = p.wellA.trim().toUpperCase();
        values[`${rd.key}_p${i + 1}_well_b`] = p.wellB.trim().toUpperCase();
      });
    });
    zeon.submit(values);
  }

  const objSelect = (val: string, set: (v: string) => void, list: typeof zeon.worldObjects) => (
    <select style={S.field} value={val} onChange={(ev) => set(ev.target.value)}>
      {list.length === 0 && <option value="">(none in world)</option>}
      {list.map((o) => { const n = objName(o); return <option key={o.uuid} value={n}>{n}</option>; })}
    </select>
  );

  // Read-only plate preview: which wells get enzyme, colored by row. F5-F8
  // (no-enzyme-blanks) are deliberately never in `wellToRow` — buffer goes there
  // by hand instead.
  const wellToRow = useMemo(() => {
    const m: Record<string, number> = {};
    ROW_DEFS.forEach((rd, ri) => {
      rows[rd.key].pairs.forEach((p) => {
        if (p.wellA) m[p.wellA.toUpperCase()] = ri;
        if (p.wellB) m[p.wellB.toUpperCase()] = ri;
      });
    });
    return m;
  }, [rows]);

  return (
    <div style={S.page}>
      <div style={S.eyebrow}>
        <span style={{ width: 7, height: 7, borderRadius: 7, background: ACCENT, display: "inline-block" }} />
        TEM-1 inhibitor screen — Part 3a of 3
      </div>
      <h1 style={S.h1}>CFPS Inhibitor Dose — Enzyme Only</h1>
      <p style={S.sub}>
        Compound (rows A-E) and vehicle (row F1-F4) are already preplated by hand — the robot's only job this
        run is enzyme, drawn from a fresh per-row aliquot tube in the reagent block and dispensed into every
        well below. Each row keeps one tip for its whole span; each duplicate pair shares a single aspirate (2x
        the per-well volume) split into two equal dispenses. F5-F8 (no-enzyme-blanks) get buffer by hand instead
        and are not touched here. Once every row is dosed, the robot seals the plate and loads it into the
        shaker/incubator with the lid closed — starting/monitoring the incubation, adding nitrocefin by hand,
        and running <code>cfps_inhibitor_kinetic_read</code> (Part 3b) to load the reader are all manual from there.
      </p>
      <hr style={S.rule} />

      <h2 style={S.h2}><span>Deck</span></h2>
      <div style={S.grid2}>
        <div><label style={S.label}>Reaction plate</label>{objSelect(reactionPlate, setReactionPlate, plateP.list)}</div>
        <div><label style={S.label}>Reagent block (enzyme aliquots)</label>{objSelect(reagentBlock, setReagentBlock, blockP.list)}</div>
        <div><label style={S.label}>Pipette</label>{objSelect(pipette, setPipette, pipetteP.list)}</div>
        <div><label style={S.label}>Tip box</label>{objSelect(tipbox, setTipbox, tipboxP.list)}</div>
      </div>

      <h2 style={S.h2}><span>Seal & incubator — after the last row is dosed</span></h2>
      <div style={S.grid2}>
        <div><label style={S.label}>Plate sealer</label>{objSelect(platesealer, setPlatesealer, sealerP.list)}</div>
        <div><label style={S.label}>Seal holder</label>{objSelect(sealHolder, setSealHolder, sealHolderP.list)}</div>
        <div><label style={S.label}>Shaker / incubator</label>{objSelect(shaker, setShaker, shakerP.list)}</div>
        <div><label style={S.label}>Plate home (seal drop target)</label>{objSelect(plateHome, setPlateHome, plateHomeP.list)}</div>
        <div>
          <label style={S.label}>Shaker slot</label>
          <input style={S.field} value={shakerSlot} onChange={(e) => setShakerSlot(e.target.value)} placeholder="slot_1" />
        </div>
        <div>
          <label style={S.label}>Seal index</label>
          <input type="number" min={1} step={1} style={S.field} value={sealIndex}
                 onChange={(e) => setSealIndex(parseInt(e.target.value || "1", 10))} />
        </div>
      </div>

      <h2 style={S.h2}><span>Enzyme volume & run</span></h2>
      <div style={S.grid2}>
        <div>
          <label style={S.label}>Enzyme per well (µL)</label>
          <input type="number" min={0} step={0.1} style={S.field} value={enzymeVolUl}
                 onChange={(e) => setEnzymeVolUl(parseFloat(e.target.value || "0"))} />
        </div>
        <div>
          <label style={S.label}>Run name (output folder)</label>
          <input style={S.field} value={runName} onChange={(e) => setRunName(e.target.value)} placeholder="cfps_inhibitor_dose_run" />
        </div>
      </div>
      <div style={{ ...S.card, background: overCapacity ? "#FBEEEB" : ACCENT_SOFT, borderColor: overCapacity ? "#E7C1B9" : "#F0C7D8" }}>
        <strong style={{ color: overCapacity ? "#8E2C1E" : ACCENT }}>
          Combined aspirate per duplicate pair: {totalVolUl.toFixed(1)} µL (2 × {enzymeVolUl} µL)
        </strong>{" "}
        against {pipette || "the selected pipette"}'s {pipetteMax} µL capacity{overCapacity ? " — exceeds it, lower the volume" : " — fits in one draw"}.
      </div>

      <h2 style={S.h2}>
        <span>Rows — one tip and one aliquot tube per row</span>
        <button type="button" style={S.smallBtn} onClick={() => loadFrom("planned")}>Load planned values</button>
      </h2>
      {stagedDiffers && (
        <div style={S.staleBox}>
          <strong>Showing the planned round, not your staged draft.</strong> Staged values come from an
          autosaved draft or a still-live run and are replayed on every open, so the synced round takes
          precedence here.{" "}
          <button type="button" style={{ ...S.smallBtn, marginLeft: 4 }} onClick={() => loadFrom("staged")}>
            Restore staged values
          </button>
        </div>
      )}

      <div style={S.plate}>
        <div />
        {COLS.map((c) => <div key={c} style={S.hdr}>{c}</div>)}
        {ROW_LETTERS.map((r) => (
          <React.Fragment key={r}>
            <div style={S.hdr}>{r}</div>
            {COLS.map((c) => {
              const w = `${r}${c}`;
              const ri = wellToRow[w];
              const active = ri !== undefined;
              const isBlank = r === "F" && c >= 5 && c <= 8;
              return (
                <div key={w} title={isBlank ? `${w} — no-enzyme blank (buffer by hand)` : w}
                     style={{ ...S.cell, background: active ? ROW_COLORS[ri % ROW_COLORS.length] : isBlank ? "#EDEDED" : "#fff", color: active ? "#fff" : isBlank ? FAINT : "#DADDD9" }}>
                  {isBlank ? "0" : ""}
                </div>
              );
            })}
          </React.Fragment>
        ))}
      </div>
      <p style={{ ...S.sub, marginTop: 8 }}>Colored = gets enzyme this run. Gray "0" (F5-F8) = no-enzyme blank, buffer by hand, robot skips it.</p>

      {ROW_DEFS.map((rd, ri) => {
        const r = rows[rd.key];
        return (
          <div key={rd.key} style={{ ...S.card, borderLeft: `4px solid ${ROW_COLORS[ri % ROW_COLORS.length]}` }}>
            <div style={S.grid4}>
              <div>
                <label style={S.label}>Row {rd.letter} — label</label>
                <input style={S.textInput} value={r.label} placeholder={rd.letter === "F" ? "vehicle_control" : "compound name"}
                       onChange={(e) => updateRow(rd.key, { label: e.target.value })} />
              </div>
              <div>
                <label style={S.label}>Enzyme src hole</label>
                <input style={S.textInput} value={r.srcHole} placeholder={`hole_${ri + 1}`}
                       onChange={(e) => updateRow(rd.key, { srcHole: e.target.value })} />
              </div>
              <div>
                <label style={S.label}>Tip index</label>
                <input style={S.numInput} value={ri + 1} disabled />
              </div>
              <div>
                <label style={S.label}>Wells this row</label>
                <div style={{ padding: "9px 0", fontFamily: MONO, fontSize: 12.5, color: MUTE }}>{r.pairs.length * 2} wells, {r.pairs.length} pair{r.pairs.length !== 1 ? "s" : ""}</div>
              </div>
            </div>
            <table style={S.table}>
              <thead>
                <tr><th style={S.th}>Pair</th><th style={S.th}>Well A</th><th style={S.th}>Well B (dup)</th></tr>
              </thead>
              <tbody>
                {r.pairs.map((p, i) => (
                  <tr key={i}>
                    <td style={S.td}>{i + 1}</td>
                    <td style={S.td}>
                      <input style={S.wellInput} value={p.wellA} onChange={(e) => updatePair(rd.key, i, { wellA: e.target.value.toUpperCase() })} />
                    </td>
                    <td style={S.td}>
                      <input style={S.wellInput} value={p.wellB} onChange={(e) => updatePair(rd.key, i, { wellB: e.target.value.toUpperCase() })} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}

      {errors.length > 0 && (
        <div style={S.errorBox}>{errors.map((m, i) => <div key={i}>• {m}</div>)}</div>
      )}

      <button type="button" style={S.button} onClick={run}>
        Confirm setup — 6 rows, 44 wells, {enzymeVolUl} µL enzyme/well
      </button>
    </div>
  );
}
