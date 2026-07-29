import React, { useEffect, useState } from "react";

declare const zeon: {
  schema: { name: string; type: string; description?: string; defaultValue?: unknown; isArray?: boolean; is_array?: boolean }[];
  worldObjects: { uuid: string; name: string; displayName?: string; meshType?: string }[];
  defaults: Record<string, unknown>;
  submit: (values: Record<string, unknown>) => void;
  setConfirmed?: (ok: boolean) => void;
  setDirty?: (dirty: boolean) => void;
  onValidationErrors: (cb: (errs: { path: string; message: string }[]) => void) => void;
};

type Obj = { uuid: string; name: string; displayName?: string; meshType?: string };
type Compound = { plate: string; well: string; label: string };

const SANS = "system-ui, -apple-system, Segoe UI, sans-serif";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
const INK = "#172033", MUTED = "#64748b", LINE = "#dbe4ee", BG = "#f5f7fb";
const COLORS: Record<string, string> = { positive: "#b45309", negative: "#64748b", vehicle: "#0f766e", compound: "#2563eb" };

const STYLE: Record<string, React.CSSProperties> = {
  page: { fontFamily: SANS, color: INK, background: BG, minHeight: "100vh", padding: "30px 24px 44px", boxSizing: "border-box" },
  content: { maxWidth: 900, margin: "0 auto" },
  eyebrow: { fontFamily: MONO, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: MUTED, marginBottom: 10 },
  h1: { fontSize: 29, lineHeight: 1.05, letterSpacing: -0.7, margin: "0 0 10px" },
  sub: { color: MUTED, fontSize: 13.5, lineHeight: 1.55, margin: "0 0 18px" },
  h2: { fontFamily: MONO, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", borderTop: `1px solid ${LINE}`, paddingTop: 18, margin: "28px 0 10px" },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 14px" },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 8 },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, color: MUTED, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 5 },
  field: { width: "100%", boxSizing: "border-box", border: `1px solid ${LINE}`, borderRadius: 8, padding: "8px 10px", background: "#fff", color: INK, fontSize: 13.5 },
  card: { border: `1px solid ${LINE}`, borderRadius: 12, padding: 14, background: "rgba(255,255,255,0.86)", marginTop: 12 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12.5 },
  th: { fontFamily: MONO, textAlign: "left", color: MUTED, borderBottom: `1px solid ${LINE}`, padding: "7px 6px", fontSize: 10.5, textTransform: "uppercase", letterSpacing: 0.4 },
  td: { borderBottom: `1px solid ${LINE}`, padding: "7px 6px", verticalAlign: "top" },
  chip: { display: "inline-block", fontFamily: MONO, fontSize: 10.5, color: "#fff", borderRadius: 999, padding: "2px 7px", marginRight: 4, marginBottom: 4 },
  error: { background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", padding: "10px 12px", borderRadius: 8, fontSize: 13, marginTop: 14 },
  button: { width: "100%", marginTop: 18, padding: "13px 16px", border: "none", borderRadius: 9, background: "#1d4ed8", color: "#fff", fontWeight: 800, cursor: "pointer", fontSize: 14.5 },
};

const HOLES = ["hole_1", "hole_2", "hole_3", "hole_4", "hole_5", "hole_6", "hole_7", "hole_8", "hole_9", "hole_10"];
const POSITIVE_WELLS = ["F3", "F7", "G11"];
const NEGATIVE_WELLS = ["D3", "D7", "E11"];
const VEHICLE_WELLS: string[] = [];
const COMPOUND_WELLS = [
  ["B2", "D2", "F2"], ["B4", "D4", "F4"], ["B6", "D6", "F6"], ["B10", "D10", "F10"],
  ["C5", "E5", "G5"], ["C9", "E9", "G9"], ["C3", "E3", "G3"], ["C7", "E7", "G7"],
];
const DEFAULT_COMPOUNDS = [
  "T1262 Tazobactam (1 uM)", "T6685 Sulbactam sodium", "T14081 Enmetazobactam", "T1008 Cephalexin",
  "T0224 Meropenem", "T0985 Oxacillin sodium salt", "T0138 Cefpiramide acid", "T8390 Cefazolin",
];
const DEFAULT_SOURCE_WELLS = ["B10", "F2", "F7", "A9", "A3", "A4", "A2", "F3"];
const DEFAULT_SOURCE_PLATES = [
  "wellplate_pcr_parts_1", "wellplate_pcr_parts_1", "wellplate_pcr_parts_1", "wellplate_pcr_parts_1",
  "wellplate_pcr_parts_2", "wellplate_pcr_parts_2", "wellplate_pcr_parts_1", "wellplate_pcr_parts_1",
];
const ACTIVE_COMPOUND_COUNT = COMPOUND_WELLS.length;

const objName = (o: Obj) => o.displayName || o.name || o.uuid;
const csv = (xs: string[]) => xs.join(",");
const upper = (s: string) => s.trim().toUpperCase();
const ul = (n: number) => `${Math.round(n * 10) / 10} uL`;

export default function Tem1ActivityScreenManualNitroR3V1SkipWorkingSolutions() {
  const schemaDefault = (name: string, fallback: unknown) => zeon.schema.find((s) => s.name === name)?.defaultValue ?? fallback;
  const initial = (name: string, fallback: unknown) => zeon.defaults[name] ?? schemaDefault(name, fallback);
  const byType = (types: string[]) => zeon.worldObjects.filter((o) => o.meshType !== undefined && types.includes(o.meshType));
  const objectOptions = (types: string[]) => {
    const xs = byType(types);
    return xs.length ? xs : zeon.worldObjects;
  };
  const firstName = (types: string[], fallback: string) => objectOptions(types)[0] ? objName(objectOptions(types)[0]) : fallback;

  const [pipette, setPipette] = useState(String(initial("pipette", firstName(["epipette_10ul", "epipette_120ul"], "epipette_10ul"))));
  const [tipbox, setTipbox] = useState(String(initial("tipbox", firstName(["tipbox_10ul", "tipbox_120ul"], "tipbox_10ul_1"))));
  const [sourceBlock, setSourceBlock] = useState(String(initial("source_block", firstName(["coldblock_wellplate", "coldblock_large", "coldblock_small"], "coldblock_wellplate"))));
  const [workingPlate, setWorkingPlate] = useState(String(initial("working_plate", firstName(["wellplate_pcr"], "wellplate_pcr_parts_4"))));
  const [assayPlate, setAssayPlate] = useState(String(initial("assay_plate", firstName(["wellplate_96_flatbottom"], "wellplate_96_flatbottom"))));
  const [plateHome, setPlateHome] = useState(String(initial("plate_home", firstName(["wellplate_holder_tags", "wellplate_holder_fixture_plate", "plate_stand_holder"], "wellplate_holder_tags"))));
  const [platesealer, setPlatesealer] = useState(String(initial("platesealer", firstName(["platesealer_platemax", "platesealer"], "platesealer_platemax_1"))));
  const [sealHolder, setSealHolder] = useState(String(initial("seal_holder", firstName(["seal_holder_stacked_reinforced", "seal_holder_stacked"], "seal_holder_stacked_reinforced_1"))));
  const [sealIndex, setSealIndex] = useState(Number(initial("seal_index", 1)));
  const [shaker, setShaker] = useState(String(initial("shaker", firstName(["wellplate_shaker"], "wellplate_shaker_1"))));
  const [shakerSlot, setShakerSlot] = useState(String(initial("shaker_slot", "slot_1")));

  const [tem1Anchor, setTem1Anchor] = useState(String(initial("tem1_working_anchor", "hole_8")));
  const [blbAnchor, setBlbAnchor] = useState(String(initial("blb_anchor", "hole_5")));
  const [noEnzymeAnchor, setNoEnzymeAnchor] = useState(String(initial("no_enzyme_anchor", "hole_6")));
  const [dmsoAnchor, setDmsoAnchor] = useState(String(initial("dmso_anchor", "hole_9")));
  const [plateMixMin, setPlateMixMin] = useState(Number(initial("plate_mix_minutes", 1)));
  const [waitMin, setWaitMin] = useState(Number(initial("preincubation_minutes", 10)));
  const [runName, setRunName] = useState(String(initial("run_name", "tem1_activity_screen_manual_nitro_r3_v1_skip_working_solutions")));

  const sourcePlates = objectOptions(["wellplate_pcr"]);
  const [positivePlate, setPositivePlate] = useState(String(initial("positive_source_plate", firstName(["wellplate_pcr"], "wellplate_pcr_parts_1"))));
  const [positiveWell, setPositiveWell] = useState(String(initial("positive_source_well", "H7")));
  const [compounds, setCompounds] = useState<Compound[]>(() =>
    COMPOUND_WELLS.map((_, i) => ({
      plate: String(initial(`compound_${i + 1}_source_plate`, DEFAULT_SOURCE_PLATES[i] || firstName(["wellplate_pcr"], "wellplate_pcr_parts_1"))),
      well: String(initial(`compound_${i + 1}_source_well`, DEFAULT_SOURCE_WELLS[i] || `A${i + 2}`)),
      label: DEFAULT_COMPOUNDS[i],
    })),
  );
  const [hostErrors, setHostErrors] = useState<string[]>([]);
  const [snapshot, setSnapshot] = useState<string | null>(null);

  const activeCompounds = compounds.slice(0, ACTIVE_COMPOUND_COUNT);
  const allCompoundWells = COMPOUND_WELLS.flat();
  const tem1Wells = [...POSITIVE_WELLS, ...VEHICLE_WELLS, ...allCompoundWells];
  const vehicleAdditionWells = [...NEGATIVE_WELLS, ...VEHICLE_WELLS];
  const allWells = [...POSITIVE_WELLS, ...NEGATIVE_WELLS, ...VEHICLE_WELLS, ...allCompoundWells];
  const enzymeVolume = 40;
  const compoundVolume = 10;
  const stockVolume = 2.5;
  const compoundBlbVolume = 47.5;
  const vehicleDmsoVolume = 5;
  const vehicleBlbVolume = 95;
  const positiveDestWell = "A1";
  const vehicleDestWell = "A2";
  const deckRows = [
    { source: "Manual TEM-1 working", location: `${sourceBlock} / ${tem1Anchor}`, serves: csv(tem1Wells), needed: tem1Wells.length * enzymeVolume, load: tem1Wells.length * enzymeVolume + 30 },
    { source: "BLB for compounds", location: `${sourceBlock} / ${blbAnchor}`, serves: "manual/pre-run working-solution prep", needed: (ACTIVE_COMPOUND_COUNT + 1) * compoundBlbVolume, load: (ACTIVE_COMPOUND_COUNT + 1) * compoundBlbVolume + 30 },
    { source: "BLB/no-enzyme", location: `${sourceBlock} / ${noEnzymeAnchor}`, serves: "manual/pre-run vehicle prep + no-TEM-1 wells", needed: vehicleBlbVolume + NEGATIVE_WELLS.length * enzymeVolume, load: vehicleBlbVolume + NEGATIVE_WELLS.length * enzymeVolume + 30 },
    { source: "DMSO", location: `${sourceBlock} / ${dmsoAnchor}`, serves: "manual/pre-run matched vehicle prep", needed: vehicleDmsoVolume, load: vehicleDmsoVolume + 5 },
    { source: "Positive + selected source stocks", location: "source wells below", serves: "manual/pre-run working-plate prep", needed: (ACTIVE_COMPOUND_COUNT + 1) * stockVolume, load: (ACTIVE_COMPOUND_COUNT + 1) * stockVolume + 10 },
    { source: "Prepared vehicle", location: `${workingPlate} / ${vehicleDestWell}`, serves: csv(vehicleAdditionWells), needed: vehicleAdditionWells.length * compoundVolume, load: vehicleAdditionWells.length * compoundVolume },
    { source: "Prepared positive control", location: `${workingPlate} / ${positiveDestWell}`, serves: csv(POSITIVE_WELLS), needed: POSITIVE_WELLS.length * compoundVolume, load: POSITIVE_WELLS.length * compoundVolume },
    ...activeCompounds.map((c, i) => ({ source: `${c.label} working`, location: `${workingPlate} / A${i + 3}`, serves: csv(COMPOUND_WELLS[i]), needed: COMPOUND_WELLS[i].length * compoundVolume, load: COMPOUND_WELLS[i].length * compoundVolume })),
    { source: "Manual nitrocefin", location: "off-protocol", serves: csv(allWells), needed: allWells.length * 25, load: allWells.length * 25 + 50 },
  ];

  const values = {
    pipette, tipbox, source_block: sourceBlock, working_plate: workingPlate, assay_plate: assayPlate, plate_home: plateHome,
    platesealer, seal_holder: sealHolder, seal_index: sealIndex, shaker, shaker_slot: shakerSlot,
    tem1_working_anchor: tem1Anchor, blb_anchor: blbAnchor, no_enzyme_anchor: noEnzymeAnchor, dmso_anchor: dmsoAnchor,
    positive_source_plate: positivePlate, positive_source_well: upper(positiveWell), positive_dest_well: positiveDestWell, vehicle_dest_well: vehicleDestWell,
    positive_wells: csv(POSITIVE_WELLS), negative_wells: csv(NEGATIVE_WELLS),
    tem1_wells: csv(tem1Wells), vehicle_addition_wells: csv(vehicleAdditionWells),
    tem1_well_count: tem1Wells.length, negative_well_count: NEGATIVE_WELLS.length, vehicle_addition_count: vehicleAdditionWells.length,
    positive_well_count: POSITIVE_WELLS.length, replicate_count: 3,
    enzyme_volume_ul: enzymeVolume, compound_volume_ul: compoundVolume, stock_volume_ul: stockVolume,
    compound_blb_volume_ul: compoundBlbVolume, vehicle_dmso_volume_ul: vehicleDmsoVolume, vehicle_blb_volume_ul: vehicleBlbVolume,
    mix_volume_ul: 10, mix_cycles: 5, plate_mix_minutes: plateMixMin, preincubation_minutes: waitMin,
    run_name: runName.trim() || "tem1_activity_screen_manual_nitro_r3_v1_skip_working_solutions",
    ...Object.fromEntries(activeCompounds.flatMap((c, i) => [
      [`compound_${i + 1}_source_plate`, c.plate],
      [`compound_${i + 1}_source_well`, upper(c.well)],
      [`compound_${i + 1}_dest_well`, `A${i + 3}`],
      [`compound_${i + 1}_wells`, csv(COMPOUND_WELLS[i])],
    ])),
  };
  const live = JSON.stringify(values);

  function localErrors() {
    const e: string[] = [];
    if (!pipette || !tipbox || !sourceBlock || !workingPlate || !assayPlate || !plateHome || !platesealer || !sealHolder || !shaker) e.push("Select all required world objects.");
    if (!(sealIndex >= 1)) e.push("Seal index must be 1 or greater.");
    if (!(plateMixMin >= 0)) e.push("Plate mix time must be zero or positive.");
    if (!(waitMin >= 0)) e.push("Sealed incubation time must be zero or positive.");
    const wellRe = /^[A-H](?:[1-9]|1[0-2])$/;
    if (!wellRe.test(upper(positiveWell))) e.push("Positive-control source well must be A1-H12.");
    activeCompounds.forEach((c, i) => {
      if (!c.plate) e.push(`Select a source plate for compound ${i + 1}.`);
      if (!wellRe.test(upper(c.well))) e.push(`Compound ${i + 1} source well must be A1-H12.`);
    });
    const sourceKeys = [["Positive control", positivePlate, upper(positiveWell)], ...activeCompounds.map((c, i) => [`Compound ${i + 1}`, c.plate, upper(c.well)] as string[])];
    const duplicateSources = sourceKeys.filter((x, i) => sourceKeys.findIndex((y) => y[1] === x[1] && y[2] === x[2]) !== i);
    if (duplicateSources.length) e.push(`Duplicate stock source locations: ${duplicateSources.map((x) => `${x[0]} ${x[1]}/${x[2]}`).join(", ")}.`);
    return e;
  }
  const errors = [...localErrors(), ...hostErrors];
  const confirmed = snapshot !== null && snapshot === live && errors.length === 0;

  useEffect(() => zeon.onValidationErrors((errs) => setHostErrors(errs.map((e) => `${e.path}: ${e.message}`))), []);
  useEffect(() => { zeon.setConfirmed?.(confirmed); }, [confirmed]);
  useEffect(() => { zeon.setDirty?.(!confirmed); }, [confirmed]);

  const selectObj = (value: string, set: (v: string) => void, opts: Obj[]) => {
    const names = opts.map(objName);
    const merged = names.includes(value) || !value ? opts : [{ uuid: value, name: value }, ...opts];
    return <select style={STYLE.field} value={value} onChange={(e) => set(e.target.value)}>{merged.map((o) => <option key={o.uuid} value={objName(o)}>{objName(o)}</option>)}</select>;
  };
  const holeSelect = (value: string, set: (v: string) => void) => <select style={STYLE.field} value={value} onChange={(e) => set(e.target.value)}>{HOLES.map((h) => <option key={h} value={h}>{h}</option>)}</select>;
  const updateCompound = (i: number, patch: Partial<Compound>) => setCompounds((xs) => xs.map((c, j) => j === i ? { ...c, ...patch } : c));
  const chip = (text: string, kind: string) => <span style={{ ...STYLE.chip, background: COLORS[kind] }}>{text}</span>;

  return (
    <div style={STYLE.page}>
      <div style={STYLE.content}>
        <div style={STYLE.eyebrow}>TEM-1 beta-lactamase · manual nitrocefin round</div>
        <h1 style={STYLE.h1}>Manual-Nitro Activity Screen</h1>
        <p style={STYLE.sub}>Working-solution preparation is skipped. Start with positive control, vehicle, and 8 R3 v1 compound working solutions already in the working plate; the robot grabs the pipette, dispenses TEM-1 solution first, loads the assay plate, seals before shaking, incubates sealed for 10 minutes, and stops. Manually unseal and add nitrocefin after the saved run.</p>

        <h2 style={STYLE.h2}>Run Timing</h2>
        <div style={STYLE.grid2}>
          <div><label style={STYLE.label}>Plate mix minutes</label><input style={STYLE.field} type="number" min={0} step={0.25} value={plateMixMin} onChange={(e) => setPlateMixMin(Number(e.target.value))} /></div>
          <div><label style={STYLE.label}>Sealed incubation minutes</label><input style={STYLE.field} type="number" min={0} step={0.5} value={waitMin} onChange={(e) => setWaitMin(Number(e.target.value))} /></div>
          <div><label style={STYLE.label}>Run name</label><input style={STYLE.field} value={runName} onChange={(e) => setRunName(e.target.value)} /></div>
          <div><label style={STYLE.label}>Seal index</label><input style={STYLE.field} type="number" min={1} step={1} value={sealIndex} onChange={(e) => setSealIndex(Number(e.target.value))} /></div>
        </div>

        <h2 style={STYLE.h2}>Deck Objects</h2>
        <div style={STYLE.grid2}>
          <div><label style={STYLE.label}>Starting pipette</label>{selectObj(pipette, setPipette, objectOptions(["epipette_10ul", "epipette_120ul"]))}</div>
          <div><label style={STYLE.label}>Starting tip box</label>{selectObj(tipbox, setTipbox, objectOptions(["tipbox_10ul", "tipbox_120ul"]))}</div>
          <div><label style={STYLE.label}>Cold block</label>{selectObj(sourceBlock, setSourceBlock, objectOptions(["coldblock_wellplate", "coldblock_large", "coldblock_small"]))}</div>
          <div><label style={STYLE.label}>Working PCR plate</label>{selectObj(workingPlate, setWorkingPlate, objectOptions(["wellplate_pcr"]))}</div>
          <div><label style={STYLE.label}>Assay plate</label>{selectObj(assayPlate, setAssayPlate, objectOptions(["wellplate_96_flatbottom"]))}</div>
          <div><label style={STYLE.label}>Plate home</label>{selectObj(plateHome, setPlateHome, objectOptions(["wellplate_holder_tags", "wellplate_holder_fixture_plate", "plate_stand_holder"]))}</div>
          <div><label style={STYLE.label}>Plate sealer</label>{selectObj(platesealer, setPlatesealer, objectOptions(["platesealer_platemax", "platesealer"]))}</div>
          <div><label style={STYLE.label}>Seal holder</label>{selectObj(sealHolder, setSealHolder, objectOptions(["seal_holder_stacked_reinforced", "seal_holder_stacked"]))}</div>
          <div><label style={STYLE.label}>Plate shaker</label>{selectObj(shaker, setShaker, objectOptions(["wellplate_shaker"]))}</div>
          <div><label style={STYLE.label}>Shaker slot</label><select style={STYLE.field} value={shakerSlot} onChange={(e) => setShakerSlot(e.target.value)}>{["slot_1", "slot_2", "slot_3", "slot_4"].map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
        </div>

        <h2 style={STYLE.h2}>Cold-Block Sources</h2>
        <div style={STYLE.grid4}>
          <div><label style={STYLE.label}>Manual TEM-1 working</label>{holeSelect(tem1Anchor, setTem1Anchor)}</div>
          <div><label style={STYLE.label}>BLB for compounds</label>{holeSelect(blbAnchor, setBlbAnchor)}</div>
          <div><label style={STYLE.label}>No-enzyme / vehicle BLB</label>{holeSelect(noEnzymeAnchor, setNoEnzymeAnchor)}</div>
          <div><label style={STYLE.label}>DMSO</label>{holeSelect(dmsoAnchor, setDmsoAnchor)}</div>
        </div>

        <h2 style={STYLE.h2}>Source Stocks</h2>
        <p style={STYLE.sub}>
          This table is the source of truth for the selected R3 v1 stock compounds. On confirm, these exact source plate/source well values are submitted as <span style={{ fontFamily: MONO }}>compound_N_source_plate</span> and <span style={{ fontFamily: MONO }}>compound_N_source_well</span>; the prep skill logs the same stock-source mapping before it transfers anything.
        </p>
        <div style={STYLE.card}>
          <table style={STYLE.table}>
            <thead><tr><th style={STYLE.th}>Condition</th><th style={STYLE.th}>Stock source plate</th><th style={STYLE.th}>Stock source well aspirated</th><th style={STYLE.th}>Working stock created</th><th style={STYLE.th}>Assay wells served later</th></tr></thead>
            <tbody>
              <tr><td style={STYLE.td}>Positive control</td><td style={STYLE.td}>{selectObj(positivePlate, setPositivePlate, sourcePlates)}</td><td style={STYLE.td}><input style={STYLE.field} value={positiveWell} onChange={(e) => setPositiveWell(e.target.value)} /></td><td style={STYLE.td}>{workingPlate} / {positiveDestWell}</td><td style={STYLE.td}>{csv(POSITIVE_WELLS)}</td></tr>
              {activeCompounds.map((c, i) => <tr key={i}><td style={STYLE.td}>{c.label}</td><td style={STYLE.td}>{selectObj(c.plate, (v) => updateCompound(i, { plate: v }), sourcePlates)}</td><td style={STYLE.td}><input style={STYLE.field} value={c.well} onChange={(e) => updateCompound(i, { well: e.target.value })} /></td><td style={STYLE.td}>{workingPlate} / A{i + 3}</td><td style={STYLE.td}>{csv(COMPOUND_WELLS[i])}</td></tr>)}
            </tbody>
          </table>
        </div>

        <h2 style={STYLE.h2}>Deck Loading Volumes</h2>
        <div style={STYLE.card}>
          <table style={STYLE.table}>
            <thead><tr><th style={STYLE.th}>Source</th><th style={STYLE.th}>Deck location</th><th style={STYLE.th}>Serves</th><th style={STYLE.th}>Transfer needed</th><th style={STYLE.th}>Load at least</th></tr></thead>
            <tbody>{deckRows.map((r) => <tr key={r.source}><td style={STYLE.td}>{r.source}</td><td style={STYLE.td}>{r.location}</td><td style={STYLE.td}>{r.serves}</td><td style={STYLE.td}>{ul(r.needed)}</td><td style={{ ...STYLE.td, fontWeight: 800 }}>{ul(r.load)}</td></tr>)}</tbody>
          </table>
        </div>

        <h2 style={STYLE.h2}>Plate Layout</h2>
        <div style={STYLE.card}>
          <p style={STYLE.sub}>{chip("Positive", "positive")} {csv(POSITIVE_WELLS)} {chip("No TEM-1", "negative")} {csv(NEGATIVE_WELLS)} {chip("8 R3 v1 compounds", "compound")} {allCompoundWells.length} wells</p>
          <table style={STYLE.table}><tbody>{["A", "B", "C", "D", "E", "F", "G", "H"].map((row) => <tr key={row}>{Array.from({ length: 12 }, (_, i) => `${row}${i + 1}`).map((w) => { const kind = POSITIVE_WELLS.includes(w) ? "positive" : NEGATIVE_WELLS.includes(w) ? "negative" : VEHICLE_WELLS.includes(w) ? "vehicle" : allCompoundWells.includes(w) ? "compound" : ""; return <td key={w} style={{ ...STYLE.td, width: "8.3%", color: kind ? COLORS[kind] : MUTED, fontFamily: MONO, fontWeight: kind ? 800 : 400 }}>{w}</td>; })}</tr>)}</tbody></table>
          <p style={{ ...STYLE.sub, marginTop: 10 }}>Per well before manual nitrocefin: 40 uL TEM-1/no-enzyme prep + 10 uL compound/control = 50 uL. After this workflow finishes, manually unseal and add nitrocefin outside the protocol.</p>
        </div>

        {errors.length > 0 && <div style={STYLE.error}>{errors.map((e, i) => <div key={i}>- {e}</div>)}</div>}
        <button type="button" style={STYLE.button} onClick={() => { const e = localErrors(); setHostErrors([]); if (e.length === 0) { zeon.submit(values); setSnapshot(live); } }}>
          {confirmed ? "Setup confirmed" : `Confirm manual-nitro screen (${waitMin || 0} min sealed incubation)`}
        </button>
      </div>
    </div>
  );
}
