// Canvas for the `pipette_demo` workflow.
//
// A deliberately tiny run-setup screen: pick the pipette and tip rack, then the
// source and destination wells and the volume. Everything else in the workflow
// is fixed.
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

// Which world objects may fill each role, by mesh type.
const PIPETTE_TYPES = ["epipette_10ul", "epipette_120ul"];
const TIPBOX_TYPES = ["tipbox_10ul", "tipbox_120ul"];
const PLATE_TYPES = ["wellplate_pcr", "wellplate_96_flatbottom"];

const ROWS = ["A", "B", "C", "D", "E", "F", "G", "H"];
const COLS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];
const TIP_COUNT = 96;

type WorldObject = { uuid: string; name: string; displayName?: string; meshType?: string };

const objName = (o: WorldObject) => o.displayName || o.name || o.uuid;

const S: Record<string, React.CSSProperties> = {
  page: { fontFamily: "system-ui, sans-serif", color: "#0f172a", padding: 24, maxWidth: 460, margin: "0 auto" },
  h1: { fontSize: 18, fontWeight: 700, margin: "0 0 4px" },
  sub: { fontSize: 13, color: "#64748b", margin: "0 0 20px", lineHeight: 1.4 },
  section: { fontSize: 11, fontWeight: 700, letterSpacing: 0.6, textTransform: "uppercase", color: "#94a3b8", margin: "24px 0 0" },
  label: { display: "block", fontSize: 13, fontWeight: 600, margin: "14px 0 6px" },
  field: { width: "100%", boxSizing: "border-box", padding: "8px 10px", fontSize: 14, border: "1px solid #cbd5e1", borderRadius: 8, background: "#fff" },
  row: { display: "flex", gap: 8 },
  hint: { fontSize: 12, color: "#64748b", marginTop: 6, lineHeight: 1.4 },
  errorBox: { background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 8, padding: "10px 12px", marginTop: 16, fontSize: 13, color: "#b91c1c" },
  button: { width: "100%", marginTop: 24, padding: "11px 16px", fontSize: 15, fontWeight: 600, color: "#fff", background: "#0e7490", border: "none", borderRadius: 8, cursor: "pointer" },
};

/** Pick the initial value for an object role: the workflow default when it is
 *  actually in this world, else the first candidate, else "". */
function initialObject(inputName: string, candidates: WorldObject[]): string {
  const d = zeon.defaults?.[inputName];
  if (typeof d === "string" && candidates.some((c) => objName(c) === d)) return d;
  return candidates[0] ? objName(candidates[0]) : "";
}

function ObjectSelect(props: {
  id: string;
  value: string;
  options: WorldObject[];
  emptyLabel: string;
  onChange: (v: string) => void;
}) {
  if (props.options.length === 0) return <div style={S.errorBox}>{props.emptyLabel}</div>;
  return (
    <select id={props.id} style={S.field} value={props.value} onChange={(e) => props.onChange(e.target.value)}>
      {props.options.map((o) => {
        const n = objName(o);
        return <option key={o.uuid} value={n}>{n}</option>;
      })}
    </select>
  );
}

function WellSelect(props: { label: string; row: string; col: number; onRow: (v: string) => void; onCol: (v: number) => void }) {
  return (
    <>
      <label style={S.label}>{props.label}</label>
      <div style={S.row}>
        <select aria-label={`${props.label} row`} style={S.field} value={props.row} onChange={(e) => props.onRow(e.target.value)}>
          {ROWS.map((r) => <option key={r} value={r}>{r}</option>)}
        </select>
        <select aria-label={`${props.label} column`} style={S.field} value={props.col} onChange={(e) => props.onCol(Number(e.target.value))}>
          {COLS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>
    </>
  );
}

export default function PipetteDemoScreen() {
  const byType = (types: string[]) =>
    zeon.worldObjects.filter((o) => o.meshType !== undefined && types.includes(o.meshType));

  const pipettes = useMemo(() => byType(PIPETTE_TYPES), []);
  const tipboxes = useMemo(() => byType(TIPBOX_TYPES), []);
  const plates = useMemo(() => byType(PLATE_TYPES), []);

  const [pipette, setPipette] = useState(() => initialObject("pipette", pipettes));
  const [tipbox, setTipbox] = useState(() => initialObject("tipbox", tipboxes));
  const [tipIndex, setTipIndex] = useState<number>(() => {
    const d = zeon.defaults?.tip_index;
    return typeof d === "number" ? d : 0;
  });
  const [sourcePlate, setSourcePlate] = useState(() => initialObject("source_plate", plates));
  const [sourceRow, setSourceRow] = useState("A");
  const [sourceCol, setSourceCol] = useState(1);
  const [destPlate, setDestPlate] = useState(() => initialObject("dest_plate", plates));
  const [destRow, setDestRow] = useState("A");
  const [destCol, setDestCol] = useState(1);
  const [volume, setVolume] = useState<number>(() => {
    const d = zeon.defaults?.volume;
    return typeof d === "number" ? d : 5;
  });
  const [errors, setErrors] = useState<string[]>([]);

  // Surface any host-side validation rejections too.
  useEffect(() => {
    zeon.onValidationErrors((errs) => setErrors(errs.map((e) => e.message)));
  }, []);

  const sourceWell = `${sourceRow}${sourceCol}`;
  const destWell = `${destRow}${destCol}`;

  function validate(): string[] {
    const errs: string[] = [];
    if (!pipette) errs.push("Select a pipette.");
    if (!tipbox) errs.push("Select a tip rack.");
    if (!Number.isInteger(tipIndex) || tipIndex < 0 || tipIndex > TIP_COUNT)
      errs.push(`Tip position must be 0 (next tip) or a whole number between 1 and ${TIP_COUNT}.`);
    if (!sourcePlate) errs.push("Select a plate to aspirate from.");
    if (!destPlate) errs.push("Select a plate to dispense into.");
    if (sourcePlate && sourcePlate === destPlate && sourceWell === destWell)
      errs.push("Source and destination are the same well.");
    if (!Number.isFinite(volume) || volume <= 0) errs.push("Volume must be a positive number of µL.");
    return errs;
  }

  function run() {
    const errs = validate();
    setErrors(errs);
    if (errs.length) return;
    zeon.submit({
      pipette,
      tipbox,
      tip_index: tipIndex,
      source_plate: sourcePlate,
      source_well: sourceWell,
      dest_plate: destPlate,
      dest_well: destWell,
      volume,
    });
  }

  const ready = pipettes.length > 0 && tipboxes.length > 0 && plates.length > 0;

  return (
    <div style={S.page}>
      <h1 style={S.h1}>Pipette Demo</h1>
      <p style={S.sub}>
        Pick up the pipette, latch a fresh tip, move one volume from a source well to a destination
        well, then eject the tip and put the pipette back.
      </p>

      <div style={S.section}>Hardware</div>

      <label style={S.label} htmlFor="pipette">Pipette</label>
      <ObjectSelect id="pipette" value={pipette} options={pipettes} onChange={setPipette}
        emptyLabel="No electronic pipettes found in this world." />

      <label style={S.label} htmlFor="tipbox">Tip rack</label>
      <ObjectSelect id="tipbox" value={tipbox} options={tipboxes} onChange={setTipbox}
        emptyLabel="No tip racks found in this world." />

      <label style={S.label} htmlFor="tip_index">Tip position</label>
      <input id="tip_index" type="number" min={0} max={TIP_COUNT} step={1} style={S.field}
        value={tipIndex} onChange={(e) => setTipIndex(parseInt(e.target.value, 10))} />
      <div style={S.hint}>
        {tipIndex === 0
          ? "Takes the rack's next tip and advances its counter."
          : `Uses tip ${tipIndex} without moving the rack counter.`}
      </div>

      <div style={S.section}>Transfer</div>

      <label style={S.label} htmlFor="source_plate">From plate</label>
      <ObjectSelect id="source_plate" value={sourcePlate} options={plates} onChange={setSourcePlate}
        emptyLabel="No well plates found in this world." />
      <WellSelect label="From well" row={sourceRow} col={sourceCol} onRow={setSourceRow} onCol={setSourceCol} />

      <label style={S.label} htmlFor="dest_plate">To plate</label>
      <ObjectSelect id="dest_plate" value={destPlate} options={plates} onChange={setDestPlate}
        emptyLabel="No well plates found in this world." />
      <WellSelect label="To well" row={destRow} col={destCol} onRow={setDestRow} onCol={setDestCol} />

      <label style={S.label} htmlFor="volume">Volume (µL)</label>
      <input id="volume" type="number" min={0.1} step={0.1} style={S.field}
        value={volume} onChange={(e) => setVolume(parseFloat(e.target.value))} />

      {errors.length > 0 && (
        <div style={S.errorBox}>
          {errors.map((m, i) => <div key={i}>• {m}</div>)}
        </div>
      )}

      <button type="button" style={S.button} onClick={run} disabled={!ready}>
        Transfer {volume} µL: {sourceWell} → {destWell}
      </button>
    </div>
  );
}
