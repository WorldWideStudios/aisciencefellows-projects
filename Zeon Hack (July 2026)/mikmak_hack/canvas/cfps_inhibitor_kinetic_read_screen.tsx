// Canvas for the `cfps_inhibitor_kinetic_read` workflow (Part 3b of the TEM-1 screen).
//
// Run after cfps_inhibitor_dose (Part 3a) has dosed compound, the compound has
// incubated with the enzyme off-robot, and the operator has added nitrocefin to
// every well by hand. Loads the plate into the reader and closes the lid — the
// operator starts the kinetic (A490) read in Gen5 by hand and retrieves the
// plate afterwards. No dose picking here; this run only touches deck objects.
//
// Sandboxed iframe contract: only `react` may be imported, no network/FS, all host
// communication via the injected `zeon.*` globals; `export default` the component.
// Object inputs submit the world-object NAME (never a UUID).

import React, { useEffect, useMemo, useState } from "react";

declare const zeon: {
  schema: { name: string; type: string; description?: string; defaultValue?: unknown; isArray?: boolean }[];
  worldObjects: { uuid: string; name: string; displayName?: string; meshType?: string }[];
  defaults: Record<string, unknown>;
  submit: (values: Record<string, unknown>) => void;
  onValidationErrors: (cb: (errs: { path: string; message: string }[]) => void) => void;
  resetInputs?: () => void;
};

const SANS = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif";
const MONO = "ui-monospace, 'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace";
const INK = "#16231C", MUTE = "#5B6B62";
const LINE = "#E3E8E3", PAPER = "#FCFCFA";
const ACCENT = "#9D174D", ACCENT_SOFT = "#FBEAF1"; // same family accent as Part 3a (nitrocefin-red)

const S: Record<string, React.CSSProperties> = {
  page: { fontFamily: SANS, color: INK, background: PAPER, padding: "34px 26px 46px", maxWidth: 620, margin: "0 auto", fontSize: 14, lineHeight: 1.55, WebkitFontSmoothing: "antialiased", height: "100vh", boxSizing: "border-box", overflowY: "auto" },
  eyebrow: { fontFamily: MONO, fontSize: 11, fontWeight: 600, letterSpacing: 1.6, textTransform: "uppercase", color: MUTE, margin: "0 0 12px", display: "flex", alignItems: "center", gap: 8 },
  h1: { fontFamily: SANS, fontSize: 27, fontWeight: 800, letterSpacing: -0.7, lineHeight: 1.05, margin: "0 0 10px", color: INK },
  sub: { fontSize: 13.5, color: MUTE, margin: "0 0 4px", lineHeight: 1.6, maxWidth: "62ch" },
  rule: { height: 1, background: LINE, border: 0, margin: "22px 0 2px" },
  h2: { fontFamily: MONO, fontSize: 11, fontWeight: 700, margin: "36px 0 12px", paddingTop: 18, color: INK, textTransform: "uppercase", letterSpacing: 1.3, borderTop: `1px solid ${LINE}` },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 16px" },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, fontWeight: 600, margin: "12px 0 5px", color: MUTE, textTransform: "uppercase", letterSpacing: 0.6 },
  field: { width: "100%", boxSizing: "border-box", padding: "9px 11px", fontFamily: SANS, fontSize: 13.5, border: `1px solid ${LINE}`, borderRadius: 7, background: "#fff", color: INK, outline: "none" },
  card: { border: `1px solid ${LINE}`, borderRadius: 8, padding: 14, marginTop: 20, background: "#fff" },
  errorBox: { background: "#FBEEEB", border: "1px solid #E7C1B9", borderRadius: 8, padding: "11px 13px", marginTop: 14, fontSize: 13, color: "#8E2C1E", lineHeight: 1.5 },
  button: { width: "100%", marginTop: 24, padding: "14px 16px", fontFamily: SANS, fontSize: 14.5, fontWeight: 700, letterSpacing: 0.2, color: "#fff", background: ACCENT, border: "none", borderRadius: 8, cursor: "pointer" },
};

const objName = (o: { name?: string; displayName?: string; uuid: string }) => o.displayName || o.name || o.uuid;

// Planned round (schema[].defaultValue) wins over a staged draft (zeon.defaults) —
// same precedence as the Part 3a canvas, so a synced round always shows up here too.
const plannedValue = (k: string): unknown => zeon.schema?.find((s) => s.name === k)?.defaultValue;
const stagedValue = (k: string): unknown => zeon.defaults?.[k];
const rawDefault = (k: string): unknown => {
  const p = plannedValue(k);
  if (p !== undefined && p !== null && p !== "") return p;
  return stagedValue(k);
};
const strDefault = (k: string, fb: string) =>
  (typeof rawDefault(k) === "string" && rawDefault(k) !== "" ? (rawDefault(k) as string) : fb);

export default function CfpsInhibitorKineticReadScreen() {
  const pick = (match: (m: string) => boolean, dfltKey: string, fallback: string) => {
    const all = zeon.worldObjects;
    const hits = all.filter((o) => match((o.meshType || "").toLowerCase()));
    const list = hits.length ? hits : all;
    const d = strDefault(dfltKey, fallback);
    if (d && list.some((o) => objName(o) === d)) return { list, init: d };
    if (fallback && list.some((o) => objName(o) === fallback)) return { list, init: fallback };
    return { list, init: list[0] ? objName(list[0]) : "" };
  };
  const plateP = useMemo(() => pick((m) => m.includes("wellplate") && !m.includes("coldblock") && !m.includes("holder") && !m.includes("shaker") && !m.includes("pcr"), "reaction_plate", "wellplate_96_flatbottom"), []);
  const readerP = useMemo(() => pick((m) => m.includes("reader"), "platereader", "plate_reader"), []);

  const [reactionPlate, setReactionPlate] = useState(plateP.init);
  const [platereader, setPlatereader] = useState(readerP.init);
  const [runName, setRunName] = useState(strDefault("run_name", "cfps_inhibitor_kinetic_read_run"));

  const [errors, setErrors] = useState<string[]>([]);
  useEffect(() => {
    zeon.onValidationErrors((errs) => setErrors(errs.map((e) => e.message)));
  }, []);

  function validate(): string[] {
    const e: string[] = [];
    if (!reactionPlate) e.push("Select the reaction plate.");
    if (!platereader) e.push("Select the plate reader.");
    return e;
  }

  function run() {
    const e = validate();
    setErrors(e);
    if (e.length) return;

    zeon.submit({
      reaction_plate: reactionPlate,
      platereader,
      run_name: (runName || "").trim() || "cfps_inhibitor_kinetic_read_run",
    });
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
        TEM-1 inhibitor screen — Part 3b of 3
      </div>
      <h1 style={S.h1}>CFPS Inhibitor Kinetic Read</h1>
      <p style={S.sub}>
        Run this only after Part 3a (<code>cfps_inhibitor_dose</code>) has dosed compound, the plate has
        incubated off-robot, and you've added nitrocefin to every well by hand. This loads the plate into the
        reader and closes the lid — you start the kinetic (A490) read in Gen5 yourself and retrieve the plate
        when it's done. Nothing here calls the reader automatically.
      </p>
      <hr style={S.rule} />

      <h2 style={S.h2}>Deck</h2>
      <div style={S.grid2}>
        <div><label style={S.label}>Reaction plate (dosed, nitrocefin added by hand)</label>{objSelect(reactionPlate, setReactionPlate, plateP.list)}</div>
        <div><label style={S.label}>Plate reader</label>{objSelect(platereader, setPlatereader, readerP.list)}</div>
      </div>

      <h2 style={S.h2}>Run</h2>
      <div>
        <label style={S.label}>Run name (output folder)</label>
        <input style={S.field} value={runName} onChange={(e) => setRunName(e.target.value)} placeholder="cfps_inhibitor_kinetic_read_run" />
      </div>

      <div style={{ ...S.card, background: ACCENT_SOFT, borderColor: "#F0C7D8" }}>
        <strong style={{ color: ACCENT }}>Manual step after this run:</strong> start the kinetic A490 protocol
        in Gen5 yourself, then retrieve the plate from the reader when the read finishes.
      </div>

      {errors.length > 0 && (
        <div style={S.errorBox}>{errors.map((m, i) => <div key={i}>• {m}</div>)}</div>
      )}

      <button type="button" style={S.button} onClick={run}>
        Confirm setup — load plate into reader
      </button>
    </div>
  );
}
