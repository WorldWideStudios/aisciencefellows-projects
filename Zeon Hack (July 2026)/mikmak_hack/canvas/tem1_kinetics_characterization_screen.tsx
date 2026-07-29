// Canvas for the `tem1_kinetics_characterization` workflow.
//
// Standalone (non-CFPS) prerequisite round: purified TEM1 enzyme x nitrocefin
// substrate concentration grid (3x3, fixed by the workflow graph), plus an
// enzyme-only and a substrate-only blank, read kinetically. Its fit sets the
// nitrocefin working concentration and endpoint timing used by the CFPS
// inhibitor dose-response screen (Part 3).
//
// This workflow declares 84 flat inputs (11 deck/run inputs + 9 grid points x 7
// fields + 2 blanks x 5 fields) — too many for a flat form to present sensibly,
// and no canvas existed for it at all before this one. Tip indices are derived
// here the same way pipeline/agents/plan_agent.py's plan_kinetics_round derives
// them (sequential, 3 per grid point then 2 per blank), so a human filling this
// canvas by hand produces the same tip layout a Plan-generated preset would.
//
// Sandboxed iframe contract: only `react` may be imported, no network/FS, all host
// communication via the injected `zeon.*` globals; `export default` the component.
// Object inputs submit the world-object NAME (never a UUID).
//
// height/overflow on S.page is a deliberate deviation from the canvas doc's "don't
// set your own scroll container" guidance — confirmed with Zeon as the right call
// for workflows with a schema this large, where the host's own auto-resize doesn't
// reliably reach every row. 100vh caps the canvas to its own iframe viewport so it
// scrolls internally no matter what height the host actually grants the iframe.

import React, { useMemo, useState } from "react";

declare const zeon: {
  schema: { name: string; type: string; description?: string; defaultValue?: unknown; isArray?: boolean }[];
  worldObjects: { uuid: string; name: string; displayName?: string; meshType?: string }[];
  // NOT the workflow's declared defaults — these are previously *staged* values:
  // a sessionStorage draft, or the saved inputs of a live (running/paused) run.
  // Empty on a clean open. The pipeline's planned numbers arrive via
  // `schema[].defaultValue` instead, which is why both are consulted below.
  defaults: Record<string, unknown>;
  submit: (values: Record<string, unknown>) => void;
  onValidationErrors: (cb: (errs: { path: string; message: string }[]) => void) => void;
  resetInputs?: () => void;
};

const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const COLS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
const WELL_ORDER = ROWS.flatMap((r) => COLS.map((c) => `${r}${c}`));
const HOLES = Array.from({ length: 10 }, (_, i) => `hole_${i + 1}`);

const GRID_POSITIONS = ["e1s1", "e1s2", "e1s3", "e2s1", "e2s2", "e2s3", "e3s1", "e3s2", "e3s3"] as const;
const GRID_LABELS: Record<string, string> = {
  e1s1: "E1 x S1", e1s2: "E1 x S2", e1s3: "E1 x S3",
  e2s1: "E2 x S1", e2s2: "E2 x S2", e2s3: "E2 x S3",
  e3s1: "E3 x S1", e3s2: "E3 x S2", e3s3: "E3 x S3",
};

const SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
const MONO = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace";
const INK = "#16231C", MUTE = "#5B6B62", FAINT = "#94A29A";
const LINE = "#E3E8E3", HAIR = "#EFF2EF", PAPER = "#FCFCFA";
const ACCENT = "#1D5D9B", ACCENT_SOFT = "#E8F0F7"; // calibration-blue signal

const S: Record<string, React.CSSProperties> = {
  page: { fontFamily: SANS, color: INK, background: PAPER, padding: "34px 26px 46px", maxWidth: 860, margin: "0 auto", fontSize: 14, lineHeight: 1.55, WebkitFontSmoothing: "antialiased", height: "100vh", boxSizing: "border-box", overflowY: "auto" },
  eyebrow: { fontFamily: MONO, fontSize: 11, fontWeight: 600, letterSpacing: 1.6, textTransform: "uppercase", color: MUTE, margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 },
  h1: { fontFamily: SANS, fontSize: 27, fontWeight: 800, letterSpacing: -0.7, lineHeight: 1.05, margin: "0 0 10px", color: INK },
  sub: { fontSize: 13.5, color: MUTE, margin: "0 0 4px", lineHeight: 1.6, maxWidth: "72ch" },
  rule: { height: 1, background: LINE, border: 0, margin: "22px 0 2px" },
  h2: { fontFamily: MONO, fontSize: 11, fontWeight: 700, margin: "36px 0 12px", paddingTop: 18, color: INK, textTransform: "uppercase", letterSpacing: 1.3, borderTop: `1px solid ${LINE}`, display: "flex", alignItems: "center", justifyContent: "space-between" },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 16px" },
  grid3: { display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "10px 16px" },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, fontWeight: 600, margin: "12px 0 5px", color: MUTE, textTransform: "uppercase", letterSpacing: 0.6 },
  field: { width: "100%", boxSizing: "border-box", padding: "9px 11px", fontFamily: SANS, fontSize: 13.5, border: `1px solid ${LINE}`, borderRadius: 7, background: "#fff", color: INK, outline: "none" },
  card: { border: `1px solid ${LINE}`, borderRadius: 8, padding: 14, marginTop: 12, background: "#fff" },
  table: { width: "100%", borderCollapse: "collapse", fontFamily: SANS, fontSize: 12.5, marginTop: 10 },
  th: { fontFamily: MONO, textAlign: "left", padding: "7px 8px", borderBottom: `1.5px solid ${INK}`, color: MUTE, fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  td: { fontFamily: SANS, textAlign: "left", padding: "6px 8px", borderBottom: `1px solid ${HAIR}` },
  numInput: { width: 72, boxSizing: "border-box", padding: "5px 7px", fontFamily: MONO, fontSize: 12.5, border: `1px solid ${LINE}`, borderRadius: 5, background: "#fff", color: INK },
  textInput: { width: 68, boxSizing: "border-box", padding: "5px 7px", fontFamily: MONO, fontSize: 12.5, border: `1px solid ${LINE}`, borderRadius: 5, background: "#fff", color: INK },
  errorBox: { background: "#FBEEEB", border: "1px solid #E7C1B9", borderRadius: 8, padding: "11px 13px", marginTop: 14, fontSize: 13, color: "#8E2C1E", lineHeight: 1.5 },
  staleBox: { background: "#FDF6E3", border: "1px solid #E5D5A8", borderRadius: 8, padding: "11px 13px", marginTop: 12, fontSize: 12.5, color: "#6B5518", lineHeight: 1.5 },
  button: { width: "100%", marginTop: 24, padding: "14px 16px", fontFamily: SANS, fontSize: 14.5, fontWeight: 700, letterSpacing: 0.2, color: "#fff", background: ACCENT, border: "none", borderRadius: 8, cursor: "pointer" },
  smallBtn: { fontFamily: MONO, fontSize: 10.5, fontWeight: 700, color: ACCENT, background: "#fff", border: `1px solid ${LINE}`, borderRadius: 5, padding: "4px 9px", cursor: "pointer", textTransform: "uppercase", letterSpacing: 0.4 },
};

const objName = (o: { name?: string; displayName?: string; uuid: string }) => o.displayName || o.name || o.uuid;

// Prefer the host's `defaults` map, then fall back to the input's own
// `defaultValue` in the schema. Those are the same value whenever the host
// populates `defaults` from the workflow — but a Plan-generated round bakes its
// numbers into `defaultValue`, so reading only `defaults` would show a blank
// form for a fully-planned round.
const plannedValue = (k: string): unknown => zeon.schema?.find((s) => s.name === k)?.defaultValue;
const stagedValue = (k: string): unknown => zeon.defaults?.[k];

// PLANNED WINS. `zeon.defaults` is staged state — an autosaved sessionStorage
// draft, or a live run's saved inputs — and the host replays it on every mount.
// `schema[].defaultValue` is what the pipeline bakes when it syncs a planned
// round. Reading staged-first meant a synced round could never appear without a
// manual click, and an old draft silently ran as if it were the new plan. So the
// declared workflow value wins, and staged only fills inputs the workflow leaves
// undeclared. `Restore staged values` puts the draft back when that's wanted.
const rawDefault = (k: string): unknown => {
  const p = plannedValue(k);
  if (p !== undefined && p !== null && p !== "") return p;
  return stagedValue(k);
};
// True when a staged draft / live-run value is masking what the workflow declares
// — i.e. the form is showing something other than the planned round.
const isStale = (k: string): boolean => {
  const d = zeon.defaults?.[k];
  if (d === undefined || d === null || d === "") return false;
  const p = plannedValue(k);
  return p !== undefined && p !== null && p !== "" && d !== p;
};
const strDefault = (k: string, fb: string) => (typeof rawDefault(k) === "string" && rawDefault(k) !== "" ? (rawDefault(k) as string) : fb);
const numDefault = (k: string, fb: number) => (typeof rawDefault(k) === "number" ? (rawDefault(k) as number) : fb);

type GridRow = { well: string; enzymeVol: number; substrateVol: number; bufferVol: number };
type BlankRow = { well: string; vol: number; bufferVol: number };

// Seeded from the workflow's own input defaults, so a round the pipeline has
// already planned and synced opens filled in rather than blank. Falls back to
// empty/zero for an unplanned workflow, which is what a human filling this in by
// hand starts from.
// `source` picks which side of the precedence to read: "auto" is the mount-time
// rule above (planned wins), "planned" and "staged" force one side, for the two
// buttons that let the operator swap between them explicitly.
type Source = "auto" | "planned" | "staged";
const pickBy = (source: Source) => {
  const get = source === "planned" ? plannedValue : source === "staged" ? stagedValue : rawDefault;
  return {
    s: (k: string, fb: string) => (typeof get(k) === "string" && get(k) !== "" ? (get(k) as string) : fb),
    n: (k: string, fb: number) => (typeof get(k) === "number" ? (get(k) as number) : fb),
  };
};

const gridRowFromDefaults = (p: string, source: Source = "auto"): GridRow => {
  const { s, n } = pickBy(source);
  return {
    well: s(`pt_${p}_well`, ""),
    enzymeVol: n(`pt_${p}_enzyme_vol_ul`, 0),
    substrateVol: n(`pt_${p}_substrate_vol_ul`, 0),
    bufferVol: n(`pt_${p}_buffer_vol_ul`, 0),
  };
};
const blankRowFromDefaults = (name: "blank_e" | "blank_s", source: Source = "auto"): BlankRow => {
  const { s, n } = pickBy(source);
  return {
    well: s(`${name}_well`, ""),
    vol: n(`${name}_vol_ul`, 0),
    bufferVol: n(`${name}_buffer_vol_ul`, 0),
  };
};

// Mirrors pipeline/agents/plan_agent.py's plan_kinetics_round tip assignment exactly:
// 3 tips per grid point in fixed order, then 2 tips for blank_e, then 2 for blank_s.
function deriveTipIndices() {
  const grid: Record<string, { enzyme: number; substrate: number; buffer: number }> = {};
  let tip = 1;
  GRID_POSITIONS.forEach((p) => {
    grid[p] = { enzyme: tip, substrate: tip + 1, buffer: tip + 2 };
    tip += 3;
  });
  const blankE = { vol: tip, buffer: tip + 1 };
  tip += 2;
  const blankS = { vol: tip, buffer: tip + 1 };
  tip += 2;
  return { grid, blankE, blankS };
}

export default function Tem1KineticsCharacterizationScreen() {
  const pick = (match: (m: string) => boolean, dfltKey: string, fallback: string) => {
    const all = zeon.worldObjects;
    const hits = all.filter((o) => match((o.meshType || "").toLowerCase()));
    const list = hits.length ? hits : all;
    const d = strDefault(dfltKey, fallback);
    if (d && list.some((o) => objName(o) === d)) return { list, init: d };
    if (fallback && list.some((o) => objName(o) === fallback)) return { list, init: fallback };
    return { list, init: list[0] ? objName(list[0]) : "" };
  };
  const pipetteP = useMemo(() => pick((m) => (m.includes("epipette") || m.includes("pipette")) && !m.includes("stand") && !m.includes("holder"), "pipette", "epipette_10ul"), []);
  const tipboxP = useMemo(() => pick((m) => m.includes("tipbox") && !m.includes("holder"), "tipbox", "tipbox_10ul_1"), []);
  const blockP = useMemo(() => pick((m) => m.includes("coldblock") && !m.includes("holder"), "reagent_block", "coldblock_wellplate"), []);
  const plateP = useMemo(() => pick((m) => m.includes("wellplate") && !m.includes("coldblock") && !m.includes("holder") && !m.includes("shaker") && !m.includes("pcr"), "reaction_plate", "wellplate_96_flatbottom"), []);
  const readerP = useMemo(() => pick((m) => m.includes("reader"), "platereader", "plate_reader"), []);
  const plateHomeP = useMemo(() => pick((m) => m.includes("holder") && m.includes("wellplate"), "plate_home", "wellplate_holder_tags"), []);

  const [pipette, setPipette] = useState(pipetteP.init);
  const [tipbox, setTipbox] = useState(tipboxP.init);
  const [reagentBlock, setReagentBlock] = useState(blockP.init);
  const [reactionPlate, setReactionPlate] = useState(plateP.init);
  const [platereader, setPlatereader] = useState(readerP.init);
  const [plateHome, setPlateHome] = useState(plateHomeP.init);
  const [enzymeHole, setEnzymeHole] = useState(strDefault("enzyme_hole", "hole_1"));
  const [substrateHole, setSubstrateHole] = useState(strDefault("substrate_hole", "hole_2"));
  const [bufferHole, setBufferHole] = useState(strDefault("buffer_hole", "hole_3"));
  const [totalWellVolume, setTotalWellVolume] = useState(numDefault("total_well_volume_ul", 20.0));
  const [runName, setRunName] = useState(strDefault("run_name", "tem1_kinetics_run"));

  const [grid, setGrid] = useState<Record<string, GridRow>>(() =>
    Object.fromEntries(GRID_POSITIONS.map((p) => [p, gridRowFromDefaults(p)])) as Record<string, GridRow>
  );
  const [blankE, setBlankE] = useState<BlankRow>(() => blankRowFromDefaults("blank_e"));
  const [blankS, setBlankS] = useState<BlankRow>(() => blankRowFromDefaults("blank_s"));

  const updateGrid = (p: string, patch: Partial<GridRow>) =>
    setGrid((g: Record<string, GridRow>) => ({ ...g, [p]: { ...g[p], ...patch } }));

  // Any per-well field where a staged draft (or a live run's saved inputs) is
  // showing something other than what the workflow declares. Worth surfacing:
  // the form silently replaying an old plate is indistinguishable from a fresh
  // one, and the two produce different chemistry.
  const stagedKeys = useMemo(() => {
    const keys: string[] = [];
    GRID_POSITIONS.forEach((p) => {
      ["well", "enzyme_vol_ul", "substrate_vol_ul", "buffer_vol_ul"].forEach((f) => {
        if (isStale(`pt_${p}_${f}`)) keys.push(`pt_${p}_${f}`);
      });
    });
    (["blank_e", "blank_s"] as const).forEach((b) => {
      ["well", "vol_ul", "buffer_vol_ul"].forEach((f) => {
        if (isStale(`${b}_${f}`)) keys.push(`${b}_${f}`);
      });
    });
    return keys;
  }, []);

  const loadFrom = (source: Source) => {
    const { s, n } = pickBy(source);
    setGrid(Object.fromEntries(GRID_POSITIONS.map((p) => [p, gridRowFromDefaults(p, source)])) as Record<string, GridRow>);
    setBlankE(blankRowFromDefaults("blank_e", source));
    setBlankS(blankRowFromDefaults("blank_s", source));
    setEnzymeHole(s("enzyme_hole", "hole_1"));
    setSubstrateHole(s("substrate_hole", "hole_2"));
    setBufferHole(s("buffer_hole", "hole_3"));
    setRunName(s("run_name", "tem1_kinetics_run"));
    setTotalWellVolume(n("total_well_volume_ul", 20.0));
  };

  const autoFillWells = () => {
    const order = [...WELL_ORDER];
    setGrid((g) => {
      const next = { ...g };
      GRID_POSITIONS.forEach((p) => { next[p] = { ...next[p], well: order.shift() || "" }; });
      return next;
    });
    setBlankE((b) => ({ ...b, well: order.shift() || "" }));
    setBlankS((b) => ({ ...b, well: order.shift() || "" }));
  };

  const tips = useMemo(() => deriveTipIndices(), []);

  const [errors, setErrors] = useState<string[]>([]);

  function validate(): string[] {
    const e: string[] = [];
    if (!pipette || !tipbox || !reagentBlock || !reactionPlate || !platereader) {
      e.push("Select the pipette, tip box, cold block, reaction plate, and plate reader.");
    }
    GRID_POSITIONS.forEach((p) => {
      const row = grid[p];
      if (!row.well.trim()) e.push(`${GRID_LABELS[p]}: set a destination well.`);
    });
    if (!blankE.well.trim()) e.push("Blank (enzyme only): set a destination well.");
    if (!blankS.well.trim()) e.push("Blank (substrate only): set a destination well.");
    return e;
  }

  function run() {
    const e = validate();
    setErrors(e);
    if (e.length) return;

    const values: Record<string, unknown> = {
      pipette, tipbox, reagent_block: reagentBlock, reaction_plate: reactionPlate,
      platereader, plate_home: plateHome,
      enzyme_hole: enzymeHole, substrate_hole: substrateHole, buffer_hole: bufferHole,
      total_well_volume_ul: totalWellVolume,
      run_name: (runName || "").trim() || "tem1_kinetics_run",
    };
    GRID_POSITIONS.forEach((p) => {
      const row = grid[p];
      const t = tips.grid[p];
      values[`pt_${p}_well`] = row.well.trim().toUpperCase();
      values[`pt_${p}_enzyme_vol_ul`] = row.enzymeVol;
      values[`pt_${p}_enzyme_tip_index`] = t.enzyme;
      values[`pt_${p}_substrate_vol_ul`] = row.substrateVol;
      values[`pt_${p}_substrate_tip_index`] = t.substrate;
      values[`pt_${p}_buffer_vol_ul`] = row.bufferVol;
      values[`pt_${p}_buffer_tip_index`] = t.buffer;
    });
    values["blank_e_well"] = blankE.well.trim().toUpperCase();
    values["blank_e_vol_ul"] = blankE.vol;
    values["blank_e_tip_index"] = tips.blankE.vol;
    values["blank_e_buffer_vol_ul"] = blankE.bufferVol;
    values["blank_e_buffer_tip_index"] = tips.blankE.buffer;
    values["blank_s_well"] = blankS.well.trim().toUpperCase();
    values["blank_s_vol_ul"] = blankS.vol;
    values["blank_s_tip_index"] = tips.blankS.vol;
    values["blank_s_buffer_vol_ul"] = blankS.bufferVol;
    values["blank_s_buffer_tip_index"] = tips.blankS.buffer;

    zeon.submit(values);
  }

  const objSelect = (val: string, set: (v: string) => void, list: typeof zeon.worldObjects) => (
    <select style={S.field} value={val} onChange={(ev) => set(ev.target.value)}>
      {list.length === 0 && <option value="">(none in world)</option>}
      {list.map((o) => { const n = objName(o); return <option key={o.uuid} value={n}>{n}</option>; })}
    </select>
  );

  const sumOf = (row: GridRow) => row.enzymeVol + row.substrateVol + row.bufferVol;

  return (
    <div style={S.page}>
      <div style={S.eyebrow}>
        <span style={{ width: 7, height: 7, borderRadius: 7, background: ACCENT, display: "inline-block" }} />
        TEM-1 inhibitor screen — prerequisite round
      </div>
      <h1 style={S.h1}>TEM1 Kinetics Characterization</h1>
      <p style={S.sub}>
        Purified TEM1 enzyme x nitrocefin substrate concentration grid (fixed 3x3), plus an
        enzyme-only and a substrate-only blank, read kinetically. This round's fit sets the
        nitrocefin working concentration and endpoint timing used by the CFPS inhibitor
        dose-response screen — run it first if that hasn't happened yet.
      </p>
      <div style={S.staleBox}>
        <strong>The run stops after the reader lid closes.</strong> The arm builds the plate, loads
        it into the reader and closes the lid — then ends. Start the kinetic read in Gen5 yourself
        and retrieve the plate afterwards; automated kinetic reads aren't available yet. The plate
        is <em>not</em> returned home, so clear the reader before the next run.
      </div>
      <hr style={S.rule} />

      <h2 style={S.h2}><span>Deck</span></h2>
      <div style={S.grid2}>
        <div><label style={S.label}>Reaction plate</label>{objSelect(reactionPlate, setReactionPlate, plateP.list)}</div>
        <div><label style={S.label}>Cold block (enzyme/substrate/buffer stock)</label>{objSelect(reagentBlock, setReagentBlock, blockP.list)}</div>
        <div><label style={S.label}>Pipette</label>{objSelect(pipette, setPipette, pipetteP.list)}</div>
        <div><label style={S.label}>Tip box</label>{objSelect(tipbox, setTipbox, tipboxP.list)}</div>
        <div><label style={S.label}>Plate reader</label>{objSelect(platereader, setPlatereader, readerP.list)}</div>
        <div><label style={S.label}>Plate home (drop target after read)</label>{objSelect(plateHome, setPlateHome, plateHomeP.list)}</div>
      </div>
      <div style={{ ...S.grid3, marginTop: 6 }}>
        <div>
          <label style={S.label}>Enzyme hole</label>
          <select style={S.field} value={enzymeHole} onChange={(e) => setEnzymeHole(e.target.value)}>
            {HOLES.map((h) => <option key={h} value={h}>{h}</option>)}
          </select>
        </div>
        <div>
          <label style={S.label}>Substrate hole</label>
          <select style={S.field} value={substrateHole} onChange={(e) => setSubstrateHole(e.target.value)}>
            {HOLES.map((h) => <option key={h} value={h}>{h}</option>)}
          </select>
        </div>
        <div>
          <label style={S.label}>Buffer hole</label>
          <select style={S.field} value={bufferHole} onChange={(e) => setBufferHole(e.target.value)}>
            {HOLES.map((h) => <option key={h} value={h}>{h}</option>)}
          </select>
        </div>
      </div>

      <h2 style={S.h2}><span>Run</span></h2>
      <div style={S.grid2}>
        <div>
          <label style={S.label}>Total well volume (uL, informational)</label>
          <input type="number" min={0} step={0.1} style={S.field} value={totalWellVolume}
                 onChange={(e) => setTotalWellVolume(parseFloat(e.target.value || "0"))} />
        </div>
        <div>
          <label style={S.label}>Run name (output folder)</label>
          <input style={S.field} value={runName} onChange={(e) => setRunName(e.target.value)} placeholder="tem1_kinetics_run" />
        </div>
      </div>

      <h2 style={S.h2}>
        <span>Enzyme x substrate grid</span>
        <span style={{ display: "flex", gap: 8 }}>
          <button type="button" style={S.smallBtn} onClick={() => loadFrom("planned")}>Load planned values</button>
          <button type="button" style={S.smallBtn} onClick={autoFillWells}>Auto-fill wells (A1, A2, ...)</button>
        </span>
      </h2>
      {stagedKeys.length > 0 && (
        <div style={S.staleBox}>
          <strong>Showing the planned round, not your staged draft.</strong> {stagedKeys.length} field
          {stagedKeys.length === 1 ? " differs" : "s differ"} between them. Staged values come from an
          autosaved draft or a still-live run and are replayed on every open, so the synced round takes
          precedence here.{" "}
          <button type="button" style={{ ...S.smallBtn, marginLeft: 4 }} onClick={() => loadFrom("staged")}>
            Restore staged values
          </button>
        </div>
      )}
      <p style={S.sub}>
        Each row's three volumes should sum to the total well volume above — the workflow itself
        doesn't enforce this, so mismatches are flagged here only as a hint, not blocked.
        Tip indices are assigned automatically (3 per grid point, in the order below).
      </p>
      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.th}>Point</th><th style={S.th}>Well</th>
            <th style={S.th}>Enzyme µL</th><th style={S.th}>Substrate µL</th><th style={S.th}>Buffer µL</th>
            <th style={S.th}>Sum</th>
          </tr>
        </thead>
        <tbody>
          {GRID_POSITIONS.map((p) => {
            const row = grid[p];
            const sum = sumOf(row);
            const mismatch = totalWellVolume > 0 && Math.abs(sum - totalWellVolume) > 0.01;
            return (
              <tr key={p}>
                <td style={{ ...S.td, fontFamily: MONO, fontWeight: 700 }}>{GRID_LABELS[p]}</td>
                <td style={S.td}>
                  <input style={S.textInput} value={row.well} placeholder="A1"
                         onChange={(e) => updateGrid(p, { well: e.target.value.toUpperCase() })} />
                </td>
                <td style={S.td}>
                  <input type="number" min={0} step={0.1} style={S.numInput} value={row.enzymeVol}
                         onChange={(e) => updateGrid(p, { enzymeVol: parseFloat(e.target.value || "0") })} />
                </td>
                <td style={S.td}>
                  <input type="number" min={0} step={0.1} style={S.numInput} value={row.substrateVol}
                         onChange={(e) => updateGrid(p, { substrateVol: parseFloat(e.target.value || "0") })} />
                </td>
                <td style={S.td}>
                  <input type="number" min={0} step={0.1} style={S.numInput} value={row.bufferVol}
                         onChange={(e) => updateGrid(p, { bufferVol: parseFloat(e.target.value || "0") })} />
                </td>
                <td style={{ ...S.td, fontFamily: MONO, color: mismatch ? "#B3492C" : FAINT }}>{sum.toFixed(1)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <h2 style={S.h2}><span>Blanks</span></h2>
      <table style={S.table}>
        <thead>
          <tr>
            <th style={S.th}>Control</th><th style={S.th}>Well</th>
            <th style={S.th}>Vol µL</th><th style={S.th}>Buffer µL</th><th style={S.th}>Sum</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td style={{ ...S.td, fontFamily: MONO, fontWeight: 700 }}>Enzyme only</td>
            <td style={S.td}>
              <input style={S.textInput} value={blankE.well} placeholder="A1"
                     onChange={(e) => setBlankE((b) => ({ ...b, well: e.target.value.toUpperCase() }))} />
            </td>
            <td style={S.td}>
              <input type="number" min={0} step={0.1} style={S.numInput} value={blankE.vol}
                     onChange={(e) => setBlankE((b) => ({ ...b, vol: parseFloat(e.target.value || "0") }))} />
            </td>
            <td style={S.td}>
              <input type="number" min={0} step={0.1} style={S.numInput} value={blankE.bufferVol}
                     onChange={(e) => setBlankE((b) => ({ ...b, bufferVol: parseFloat(e.target.value || "0") }))} />
            </td>
            <td style={{ ...S.td, fontFamily: MONO, color: FAINT }}>{(blankE.vol + blankE.bufferVol).toFixed(1)}</td>
          </tr>
          <tr>
            <td style={{ ...S.td, fontFamily: MONO, fontWeight: 700 }}>Substrate only</td>
            <td style={S.td}>
              <input style={S.textInput} value={blankS.well} placeholder="A1"
                     onChange={(e) => setBlankS((b) => ({ ...b, well: e.target.value.toUpperCase() }))} />
            </td>
            <td style={S.td}>
              <input type="number" min={0} step={0.1} style={S.numInput} value={blankS.vol}
                     onChange={(e) => setBlankS((b) => ({ ...b, vol: parseFloat(e.target.value || "0") }))} />
            </td>
            <td style={S.td}>
              <input type="number" min={0} step={0.1} style={S.numInput} value={blankS.bufferVol}
                     onChange={(e) => setBlankS((b) => ({ ...b, bufferVol: parseFloat(e.target.value || "0") }))} />
            </td>
            <td style={{ ...S.td, fontFamily: MONO, color: FAINT }}>{(blankS.vol + blankS.bufferVol).toFixed(1)}</td>
          </tr>
        </tbody>
      </table>

      <div style={{ ...S.card, background: ACCENT_SOFT, borderColor: "#C9DCEC" }}>
        <strong style={{ color: ACCENT }}>Tip indices are assigned automatically</strong> — 3 tips per grid
        point (enzyme, substrate, buffer) in the order shown above, then 2 each for the enzyme-only and
        substrate-only blanks (tips 1..{3 * GRID_POSITIONS.length + 4} total). Make sure the tip box has
        enough fresh tips before running.
      </div>

      {errors.length > 0 && (
        <div style={S.errorBox}>{errors.map((m, i) => <div key={i}>• {m}</div>)}</div>
      )}

      <button type="button" style={S.button} onClick={run}>
        Confirm setup — {GRID_POSITIONS.length + 2} wells
      </button>
    </div>
  );
}
