// Canvas for the `pipette_demo` workflow.
//
// A deliberately tiny run-setup screen: choose which PCR plate to go to, which
// well, and how much to aspirate. Everything else in the workflow is fixed.
//
// Sandboxed iframe contract: only `react` may be imported, no network/FS, and
// all host communication goes through the injected `zeon.*` globals. The
// component must `export default`. Object inputs submit the world-object NAME
// (e.g. "wellplate_pcr_parts_1"), never a UUID.

import React, { useEffect, useMemo, useState } from "react";

declare const zeon: {
  schema: { name: string; type: string; description?: string; defaultValue?: unknown; is_array?: boolean }[];
  worldObjects: { uuid: string; name: string; displayName?: string; meshType?: string; anchors?: string[] }[];
  defaults: Record<string, unknown>;
  submit: (values: Record<string, unknown>) => void;
  onValidationErrors: (cb: (errs: { path: string; message: string }[]) => void) => void;
};

// The aspirate skill operates on a PCR plate; only offer those as targets.
const PLATE_MESH_TYPE = "wellplate_pcr";
const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const COLS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

const objName = (o: { name?: string; displayName?: string; uuid: string }) =>
  o.displayName || o.name || o.uuid;

const S: Record<string, React.CSSProperties> = {
  page: { fontFamily: "system-ui, sans-serif", color: "#0f172a", padding: 24, maxWidth: 460, margin: "0 auto" },
  h1: { fontSize: 18, fontWeight: 700, margin: "0 0 4px" },
  sub: { fontSize: 13, color: "#64748b", margin: "0 0 20px", lineHeight: 1.4 },
  label: { display: "block", fontSize: 13, fontWeight: 600, margin: "16px 0 6px" },
  field: { width: "100%", boxSizing: "border-box", padding: "8px 10px", fontSize: 14, border: "1px solid #cbd5e1", borderRadius: 8, background: "#fff" },
  wellRow: { display: "flex", gap: 8 },
  err: { color: "#b91c1c", fontSize: 12, marginTop: 4 },
  errorBox: { background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "10px 12px", marginTop: 16, fontSize: 13, color: "#b91c1c" },
  button: { width: "100%", marginTop: 24, padding: "11px 16px", fontSize: 15, fontWeight: 600, color: "#fff", background: "#0e7490", border: "none", borderRadius: 8, cursor: "pointer" },
};

export default function PipetteDemoScreen() {
  const plates = useMemo(
    () => zeon.worldObjects.filter((o) => o.meshType === PLATE_MESH_TYPE),
    [],
  );

  const [plate, setPlate] = useState<string>(() => {
    const d = zeon.defaults?.plate;
    if (typeof d === "string" && plates.some((p) => objName(p) === d)) return d;
    return plates[0] ? objName(plates[0]) : "";
  });
  const [row, setRow] = useState("A");
  const [col, setCol] = useState(1);
  const [volume, setVolume] = useState<number>(() => {
    const d = zeon.defaults?.volume;
    return typeof d === "number" ? d : 5;
  });
  const [errors, setErrors] = useState<string[]>([]);

  // Surface any host-side validation rejections too.
  useEffect(() => {
    zeon.onValidationErrors((errs) => setErrors(errs.map((e) => e.message)));
  }, []);

  const well = `${row}${col}`;

  function validate(): string[] {
    const errs: string[] = [];
    if (!plate) errs.push("Select a plate to aspirate from.");
    else if (!plates.some((p) => objName(p) === plate)) errs.push(`Plate "${plate}" is not in the world.`);
    if (!ROWS.includes(row) || !COLS.includes(col)) errs.push(`Well "${well}" is not a valid A1–H12 well.`);
    if (!Number.isFinite(volume) || volume <= 0) errs.push("Volume must be a positive number of µL.");
    return errs;
  }

  function run() {
    const errs = validate();
    setErrors(errs);
    if (errs.length) return;
    zeon.submit({ plate, well, volume });
  }

  return (
    <div style={S.page}>
      <h1 style={S.h1}>Pipette Demo</h1>
      <p style={S.sub}>
        Pick up the pipette, grab a fresh tip, and aspirate from one well. Choose where to go below.
      </p>

      <label style={S.label} htmlFor="plate">Plate to aspirate from</label>
      {plates.length === 0 ? (
        <div style={S.errorBox}>No PCR wellplates found in this world.</div>
      ) : (
        <select id="plate" style={S.field} value={plate} onChange={(e) => setPlate(e.target.value)}>
          {plates.map((p) => {
            const n = objName(p);
            return <option key={p.uuid} value={n}>{n}</option>;
          })}
        </select>
      )}

      <label style={S.label}>Well</label>
      <div style={S.wellRow}>
        <select aria-label="row" style={S.field} value={row} onChange={(e) => setRow(e.target.value)}>
          {ROWS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select aria-label="column" style={S.field} value={col} onChange={(e) => setCol(Number(e.target.value))}>
          {COLS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      <label style={S.label} htmlFor="volume">Volume (µL)</label>
      <input
        id="volume"
        type="number"
        min={0.1}
        step={0.1}
        style={S.field}
        value={volume}
        onChange={(e) => setVolume(parseFloat(e.target.value))}
      />

      {errors.length > 0 && (
        <div style={S.errorBox}>
          {errors.map((m, i) => <div key={i}>• {m}</div>)}
        </div>
      )}

      <button type="button" style={S.button} onClick={run} disabled={plates.length === 0}>
        Aspirate from {well}
      </button>
    </div>
  );
}
