// Canvas for the `cfps_inhibitor_dose_response` workflow (Part 3 of the TEM-1 screen).
//
// Doses up to 8 already-expressed TEM1 wells (built by cfps_mastermix / Part 1,
// confirmed by cfps_sfgfp_confirmation / Part 2) with a compound volume from a
// pre-arrayed compound library plate plus a shared nitrocefin volume, then the
// workflow reads the plate kinetically. You:
//   - pick the deck objects (reaction plate, compound library, cold block, pipette)
//   - assign which cold-block hole holds the nitrocefin stock
//   - click up to 8 wells on the reaction plate that already hold expressed TEM1
//   - for each, set the compound source well (on the library plate) and volume,
//     plus the nitrocefin volume for that well
//
// Sandboxed iframe contract: only `react` may be imported, no network/FS, all host
// communication via the injected `zeon.*` globals; `export default` the component.
// Object inputs submit the world-object NAME (never a UUID).

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

const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const COLS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
const HOLES = Array.from({ length: 10 }, (_, i) => `hole_${i + 1}`);
const MAX_DOSES = 8;

const SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
const MONO = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace";
const INK = "#16231C", MUTE = "#5B6B62", FAINT = "#94A29A";
const LINE = "#E3E8E3", HAIR = "#EFF2EF", PAPER = "#FCFCFA";
const ACCENT = "#9D174D", ACCENT_SOFT = "#FBEAF1"; // nitrocefin-red signal

const S: Record<string, React.CSSProperties> = {
  // height/overflow here are a deliberate deviation from the canvas doc's "don't set your own
  // scroll container" guidance — confirmed with Zeon as the right call for this workflow's
  // unusually large (84-input) schema, where the host's own auto-resize wasn't reaching every
  // row. 100vh caps the canvas to its own iframe viewport so it scrolls internally no matter
  // what height the host actually grants the iframe.
  page: { fontFamily: SANS, color: INK, background: PAPER, padding: "34px 26px 46px", maxWidth: 760, margin: "0 auto", fontSize: 14, lineHeight: 1.55, WebkitFontSmoothing: "antialiased", height: "100vh", boxSizing: "border-box", overflowY: "auto" },
  eyebrow: { fontFamily: MONO, fontSize: 11, fontWeight: 600, letterSpacing: 1.6, textTransform: "uppercase", color: MUTE, margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 },
  h1: { fontFamily: SANS, fontSize: 27, fontWeight: 800, letterSpacing: -0.7, lineHeight: 1.05, margin: "0 0 10px", color: INK },
  sub: { fontSize: 13.5, color: MUTE, margin: "0 0 4px", lineHeight: 1.6, maxWidth: "68ch" },
  rule: { height: 1, background: LINE, border: 0, margin: "22px 0 2px" },
  h2: { fontFamily: MONO, fontSize: 11, fontWeight: 700, margin: "36px 0 12px", paddingTop: 18, color: INK, textTransform: "uppercase", letterSpacing: 1.3, borderTop: `1px solid ${LINE}`, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 },
  smallBtn: { fontFamily: MONO, fontSize: 10.5, fontWeight: 700, color: ACCENT, background: "#fff", border: `1px solid ${LINE}`, borderRadius: 5, padding: "4px 9px", cursor: "pointer", textTransform: "uppercase", letterSpacing: 0.4, whiteSpace: "nowrap" },
  staleBox: { background: "#FDF6E3", border: "1px solid #E5D5A8", borderRadius: 8, padding: "11px 13px", marginTop: 12, fontSize: 12.5, color: "#6B5518", lineHeight: 1.5 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 16px" },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, fontWeight: 600, margin: "12px 0 5px", color: MUTE, textTransform: "uppercase", letterSpacing: 0.6 },
  field: { width: "100%", boxSizing: "border-box", padding: "9px 11px", fontFamily: SANS, fontSize: 13.5, border: `1px solid ${LINE}`, borderRadius: 7, background: "#fff", color: INK, outline: "none" },
  card: { border: `1px solid ${LINE}`, borderRadius: 8, padding: 14, marginTop: 12, background: "#fff" },
  plate: { display: "inline-grid", gridTemplateColumns: `20px repeat(12, 27px)`, gap: 4, userSelect: "none" },
  hdr: { fontFamily: MONO, fontSize: 9.5, color: FAINT, textAlign: "center", lineHeight: "27px" },
  cell: { width: 27, height: 27, borderRadius: 5, border: `1px solid ${LINE}`, fontFamily: MONO, fontSize: 9, cursor: "pointer", color: "#fff", fontWeight: 700, padding: 0 },
  table: { width: "100%", borderCollapse: "collapse", fontFamily: SANS, fontSize: 12.5, marginTop: 10 },
  th: { fontFamily: MONO, textAlign: "left", padding: "7px 8px", borderBottom: `1.5px solid ${INK}`, color: MUTE, fontWeight: 700, fontSize: 10, textTransform: "uppercase", letterSpacing: 0.5 },
  td: { fontFamily: SANS, textAlign: "left", padding: "6px 8px", borderBottom: `1px solid ${HAIR}` },
  numInput: { width: 72, boxSizing: "border-box", padding: "5px 7px", fontFamily: MONO, fontSize: 12.5, border: `1px solid ${LINE}`, borderRadius: 5, background: "#fff", color: INK },
  textInput: { width: 68, boxSizing: "border-box", padding: "5px 7px", fontFamily: MONO, fontSize: 12.5, border: `1px solid ${LINE}`, borderRadius: 5, background: "#fff", color: INK },
  errorBox: { background: "#FBEEEB", border: "1px solid #E7C1B9", borderRadius: 8, padding: "11px 13px", marginTop: 14, fontSize: 13, color: "#8E2C1E", lineHeight: 1.5 },
  button: { width: "100%", marginTop: 24, padding: "14px 16px", fontFamily: SANS, fontSize: 14.5, fontWeight: 700, letterSpacing: 0.2, color: "#fff", background: ACCENT, border: "none", borderRadius: 8, cursor: "pointer" },
  removeBtn: { fontFamily: MONO, fontSize: 11, fontWeight: 700, color: MUTE, background: "#fff", border: `1px solid ${LINE}`, borderRadius: 5, padding: "3px 8px", cursor: "pointer" },
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

type DosePos = { well: string; compoundSrcWell: string; compoundVol: number; nitrocefinVol: number };

// A planned round declares dose_n positions; without this the table opened empty
// and every well and volume had to be re-entered by hand.
const dosesFrom = (source: Source): DosePos[] => {
  const { s, n } = pickBy(source);
  const count = Math.min(n("dose_n", 0), MAX_DOSES);
  const out: DosePos[] = [];
  for (let i = 1; i <= count; i++) {
    const well = s(`dose${i}_well`, "");
    if (!well) continue;
    out.push({
      well,
      compoundSrcWell: s(`dose${i}_compound_src_well`, ""),
      compoundVol: n(`dose${i}_compound_vol_ul`, 0),
      nitrocefinVol: n(`dose${i}_nitrocefin_vol_ul`, 0),
    });
  }
  return out;
};

export default function CfpsInhibitorDoseResponseScreen() {
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
  const libraryP = useMemo(() => pick((m) => m.includes("wellplate_pcr") || m.includes("pcr"), "compound_library", "wellplate_pcr_parts_2"), []);
  const readerP = useMemo(() => pick((m) => m.includes("reader"), "platereader", "plate_reader"), []);
  const plateHomeP = useMemo(() => pick((m) => m.includes("holder") && m.includes("wellplate"), "plate_home", "wellplate_holder_tags"), []);

  const [pipette, setPipette] = useState(pipetteP.init);
  const [tipbox, setTipbox] = useState(tipboxP.init);
  const [reagentBlock, setReagentBlock] = useState(blockP.init);
  const [reactionPlate, setReactionPlate] = useState(plateP.init);
  const [compoundLibrary, setCompoundLibrary] = useState(libraryP.init);
  const [platereader, setPlatereader] = useState(readerP.init);
  const [plateHome, setPlateHome] = useState(plateHomeP.init);
  const [nitrocefinHole, setNitrocefinHole] = useState(strDefault("nitrocefin_hole", "hole_9"));
  const [compoundId, setCompoundId] = useState(strDefault("compound_id", ""));
  const [runName, setRunName] = useState(strDefault("run_name", "cfps_inhibitor_dose_response_run"));

  // Ordered list of dose positions — seeded from the planned round if one has been
  // synced, otherwise empty for a human to build by clicking the plate map.
  const [doses, setDoses] = useState<DosePos[]>(() => dosesFrom("auto"));

  const stagedDiffers = useMemo(() => {
    const planned = dosesFrom("planned");
    const staged = dosesFrom("staged");
    if (!staged.length) return false;
    return JSON.stringify(planned) !== JSON.stringify(staged);
  }, []);
  const loadFrom = (source: Source) => {
    const { s } = pickBy(source);
    setDoses(dosesFrom(source));
    setNitrocefinHole(s("nitrocefin_hole", "hole_9"));
    setCompoundId(s("compound_id", ""));
    setRunName(s("run_name", "cfps_inhibitor_dose_response_run"));
  };

  const toggleWell = (w: string) =>
    setDoses((ds) => {
      const idx = ds.findIndex((d) => d.well === w);
      if (idx >= 0) return ds.filter((_, i) => i !== idx);
      if (ds.length >= MAX_DOSES) return ds; // capped by the workflow's fixed 8-position graph
      return [...ds, { well: w, compoundSrcWell: "", compoundVol: 0, nitrocefinVol: 0 }];
    });
  const updateDose = (i: number, patch: Partial<DosePos>) =>
    setDoses((ds) => ds.map((d, j) => (j === i ? { ...d, ...patch } : d)));
  const removeDose = (i: number) => setDoses((ds) => ds.filter((_, j) => j !== i));

  const [errors, setErrors] = useState<string[]>([]);
  useEffect(() => {
    zeon.onValidationErrors((errs) => setErrors(errs.map((e) => e.message)));
  }, []);

  function validate(): string[] {
    const e: string[] = [];
    if (!pipette || !tipbox || !reagentBlock || !reactionPlate || !compoundLibrary || !platereader) {
      e.push("Select the pipette, tip box, cold block, reaction plate, compound library, and plate reader.");
    }
    if (doses.length === 0) e.push("Click at least one well on the reaction plate — it must already hold expressed TEM1 reaction mix from Part 1.");
    doses.forEach((d, i) => {
      if (!d.compoundSrcWell.trim()) e.push(`Dose ${i + 1} (${d.well}): set a compound source well.`);
      if (!(d.compoundVol > 0)) e.push(`Dose ${i + 1} (${d.well}): compound volume must be positive.`);
      if (!(d.nitrocefinVol > 0)) e.push(`Dose ${i + 1} (${d.well}): nitrocefin volume must be positive.`);
    });
    return e;
  }

  function run() {
    const e = validate();
    setErrors(e);
    if (e.length) return;

    const values: Record<string, unknown> = {
      pipette, tipbox, reagent_block: reagentBlock, reaction_plate: reactionPlate,
      compound_library: compoundLibrary, platereader, plate_home: plateHome,
      nitrocefin_hole: nitrocefinHole, compound_id: compoundId.trim(),
      dose_n: doses.length,
      run_name: (runName || "").trim() || "cfps_inhibitor_dose_response_run",
    };
    doses.forEach((d, i) => {
      const n = i + 1;
      values[`dose${n}_well`] = d.well;
      values[`dose${n}_compound_src_well`] = d.compoundSrcWell.trim();
      values[`dose${n}_compound_vol_ul`] = d.compoundVol;
      values[`dose${n}_compound_tip_index`] = n;
      values[`dose${n}_nitrocefin_vol_ul`] = d.nitrocefinVol;
      values[`dose${n}_nitrocefin_tip_index`] = n + 8;
    });
    // Unused dose slots (up to MAX_DOSES) stay at the workflow's zero-volume defaults —
    // the graph has all 8 positions but dose_n tells later analysis how many are real.
    zeon.submit(values);
  }

  const objSelect = (val: string, set: (v: string) => void, list: typeof zeon.worldObjects) => (
    <select style={S.field} value={val} onChange={(ev) => set(ev.target.value)}>
      {list.length === 0 && <option value="">(none in world)</option>}
      {list.map((o) => { const n = objName(o); return <option key={o.uuid} value={n}>{n}</option>; })}
    </select>
  );

  return (
    <div style={S.page}>
      <div style={S.eyebrow}>
        <span style={{ width: 7, height: 7, borderRadius: 7, background: ACCENT, display: "inline-block" }} />
        TEM-1 inhibitor screen — Part 3 of 3
      </div>
      <h1 style={S.h1}>CFPS Inhibitor Dose Response</h1>
      <p style={S.sub}>
        Doses each well you pick below with a compound volume (from the compound library plate) plus a shared
        nitrocefin volume, then reads the plate kinetically — the initial slope of A490 vs time is TEM-1's
        velocity, and a real inhibitor drops it. Pick wells that already hold expressed TEM1 reaction mix from
        Part 1 (<code>cfps_mastermix</code>), confirmed by Part 2 (<code>cfps_sfgfp_confirmation</code>). No
        seal or shake here — the reader captures the time course live, in one sitting.
      </p>
      <hr style={S.rule} />

      <h2 style={S.h2}>Deck</h2>
      <div style={S.grid2}>
        <div><label style={S.label}>Reaction plate (Part-1 plate)</label>{objSelect(reactionPlate, setReactionPlate, plateP.list)}</div>
        <div><label style={S.label}>Compound library plate</label>{objSelect(compoundLibrary, setCompoundLibrary, libraryP.list)}</div>
        <div><label style={S.label}>Cold block (nitrocefin stock)</label>{objSelect(reagentBlock, setReagentBlock, blockP.list)}</div>
        <div><label style={S.label}>Pipette</label>{objSelect(pipette, setPipette, pipetteP.list)}</div>
        <div><label style={S.label}>Tip box</label>{objSelect(tipbox, setTipbox, tipboxP.list)}</div>
        <div><label style={S.label}>Plate reader</label>{objSelect(platereader, setPlatereader, readerP.list)}</div>
        <div><label style={S.label}>Plate home (drop target after read)</label>{objSelect(plateHome, setPlateHome, plateHomeP.list)}</div>
        <div>
          <label style={S.label}>Nitrocefin hole (cold block)</label>
          <select style={S.field} value={nitrocefinHole} onChange={(e) => setNitrocefinHole(e.target.value)}>
            {HOLES.map((h) => <option key={h} value={h}>{h}</option>)}
          </select>
        </div>
      </div>

      <h2 style={S.h2}>Compound & run</h2>
      <div style={S.grid2}>
        <div>
          <label style={S.label}>Compound ID (logged only)</label>
          <input style={S.field} value={compoundId} onChange={(e) => setCompoundId(e.target.value)} placeholder="e.g. cmpd_017" />
        </div>
        <div>
          <label style={S.label}>Run name (output folder)</label>
          <input style={S.field} value={runName} onChange={(e) => setRunName(e.target.value)} placeholder="cfps_inhibitor_dose_response_run" />
        </div>
      </div>

      <h2 style={S.h2}>
        <span>Wells to dose — click up to {MAX_DOSES} on the reaction plate</span>
        <button type="button" style={S.smallBtn} onClick={() => loadFrom("planned")}>Load planned values</button>
      </h2>
      <p style={S.sub}>Only click wells that already hold expressed TEM1 reaction mix from Part 1.</p>
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
        {ROWS.map((r) => (
          <React.Fragment key={r}>
            <div style={S.hdr}>{r}</div>
            {COLS.map((c) => {
              const w = `${r}${c}`;
              const idx = doses.findIndex((d) => d.well === w);
              const active = idx >= 0;
              return (
                <button key={w} type="button" title={w} onClick={() => toggleWell(w)}
                        style={{ ...S.cell, background: active ? ACCENT : "#fff", color: active ? "#fff" : FAINT }}>
                  {active ? idx + 1 : ""}
                </button>
              );
            })}
          </React.Fragment>
        ))}
      </div>

      {doses.length === 0 ? (
        <p style={{ ...S.sub, marginTop: 12 }}>No wells picked yet.</p>
      ) : (
        <table style={S.table}>
          <thead>
            <tr>
              <th style={S.th}>#</th><th style={S.th}>Well</th>
              <th style={S.th}>Compound src well</th><th style={S.th}>Compound µL</th>
              <th style={S.th}>Nitrocefin µL</th><th style={S.th}></th>
            </tr>
          </thead>
          <tbody>
            {doses.map((d, i) => (
              <tr key={d.well}>
                <td style={S.td}>{i + 1}</td>
                <td style={{ ...S.td, fontFamily: MONO, fontWeight: 700 }}>{d.well}</td>
                <td style={S.td}>
                  <input style={S.textInput} value={d.compoundSrcWell} placeholder="A1"
                         onChange={(e) => updateDose(i, { compoundSrcWell: e.target.value.toUpperCase() })} />
                </td>
                <td style={S.td}>
                  <input type="number" min={0} step={0.1} style={S.numInput} value={d.compoundVol}
                         onChange={(e) => updateDose(i, { compoundVol: parseFloat(e.target.value || "0") })} />
                </td>
                <td style={S.td}>
                  <input type="number" min={0} step={0.1} style={S.numInput} value={d.nitrocefinVol}
                         onChange={(e) => updateDose(i, { nitrocefinVol: parseFloat(e.target.value || "0") })} />
                </td>
                <td style={S.td}>
                  <button type="button" style={S.removeBtn} onClick={() => removeDose(i)}>remove</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div style={{ ...S.card, background: ACCENT_SOFT, borderColor: "#F0C7D8" }}>
        <strong style={{ color: ACCENT }}>Tip indices are assigned automatically</strong> — compound legs use
        1..{MAX_DOSES}, nitrocefin legs use {MAX_DOSES + 1}..{MAX_DOSES * 2}, in dose order. Make sure the tip box
        has at least {MAX_DOSES * 2} fresh tips before running.
      </div>

      {errors.length > 0 && (
        <div style={S.errorBox}>{errors.map((m, i) => <div key={i}>• {m}</div>)}</div>
      )}

      <button type="button" style={S.button} onClick={run}>
        Confirm setup — {doses.length} well{doses.length !== 1 ? "s" : ""} dosed
      </button>
    </div>
  );
}
