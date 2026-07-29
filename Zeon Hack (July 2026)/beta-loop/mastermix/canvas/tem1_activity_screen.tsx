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
const INK = "#1f2933", MUTED = "#62707f", LINE = "#e5e7eb", BG = "#fff7ed";
const COLORS: Record<string, string> = {
  positive: "#b45309",
  negative: "#64748b",
  vehicle: "#0f766e",
  compound: "#2563eb",
};

const STYLE: Record<string, React.CSSProperties> = {
  page: { fontFamily: SANS, color: INK, background: BG, minHeight: "100vh", padding: "30px 24px 44px", boxSizing: "border-box" },
  content: { maxWidth: 840, margin: "0 auto" },
  eyebrow: { fontFamily: MONO, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: MUTED, marginBottom: 10 },
  h1: { fontSize: 28, lineHeight: 1.05, letterSpacing: -0.6, margin: "0 0 10px" },
  sub: { color: MUTED, fontSize: 13.5, lineHeight: 1.55, margin: "0 0 18px" },
  h2: { fontFamily: MONO, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", borderTop: `1px solid ${LINE}`, paddingTop: 18, margin: "28px 0 10px" },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 14px" },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 6 },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, color: MUTED, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 5 },
  field: { width: "100%", boxSizing: "border-box", border: `1px solid ${LINE}`, borderRadius: 8, padding: "8px 10px", background: "#fff", color: INK, fontSize: 13.5 },
  card: { border: `1px solid ${LINE}`, borderRadius: 10, padding: 14, background: "rgba(255,255,255,0.78)", marginTop: 12 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12.5 },
  th: { fontFamily: MONO, textAlign: "left", color: MUTED, borderBottom: `1px solid ${LINE}`, padding: "7px 6px", fontSize: 10.5, textTransform: "uppercase", letterSpacing: 0.4 },
  td: { borderBottom: `1px solid ${LINE}`, padding: "7px 6px", verticalAlign: "top" },
  chip: { display: "inline-block", fontFamily: MONO, fontSize: 10.5, color: "#fff", borderRadius: 999, padding: "2px 7px", marginRight: 4, marginBottom: 4 },
  error: { background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", padding: "10px 12px", borderRadius: 8, fontSize: 13, marginTop: 14 },
  button: { width: "100%", marginTop: 18, padding: "13px 16px", border: "none", borderRadius: 9, background: "#c2410c", color: "#fff", fontWeight: 800, cursor: "pointer", fontSize: 14.5 },
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

export default function Tem1ActivityScreen() {
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
  const [assayPlate, setAssayPlate] = useState(String(initial("assay_plate", firstName(["wellplate_96_flatbottom"], "wellplate_96_flatbottom"))));
  const [plateHome, setPlateHome] = useState(String(initial("plate_home", firstName(["wellplate_holder_tags", "wellplate_holder_fixture_plate", "plate_stand_holder"], "wellplate_holder_tags"))));
  const [shaker, setShaker] = useState(String(initial("shaker", firstName(["wellplate_shaker"], "wellplate_shaker_1"))));
  const [shakerSlot, setShakerSlot] = useState(String(initial("shaker_slot", "slot_1")));

  const [enzymeAnchor, setEnzymeAnchor] = useState(String(initial("tem1_working_anchor", "hole_8")));
  const [noEnzymeAnchor, setNoEnzymeAnchor] = useState(String(initial("blb_anchor_2", "hole_6")));
  const [blbAnchor, setBlbAnchor] = useState(String(initial("blb_anchor", "hole_5")));
  const [nitrocefinAnchor, setNitrocefinAnchor] = useState(String(initial("nitrocefin_anchor", "hole_10")));
  const [nitrocefinBlbAnchor, setNitrocefinBlbAnchor] = useState(String(initial("nitrocefin_blb_anchor", "hole_7")));
  const [nitrocefinStockAnchor, setNitrocefinStockAnchor] = useState(String(initial("nitrocefin_stock_anchor", "hole_4")));
  const [plateMixMin, setPlateMixMin] = useState(Number(initial("plate_mix_minutes", 1)));
  const [waitMin, setWaitMin] = useState(Number(initial("preincubation_minutes", 10)));
  const [runName, setRunName] = useState(String(initial("run_name", "tem1_activity_screen_r3_v1")));
  const [sourceOverage, setSourceOverage] = useState(30);
  const [compoundOverage, setCompoundOverage] = useState(10);
  const [nitrocefinOverage, setNitrocefinOverage] = useState(50);

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

  const activeCompoundWellsByGroup = COMPOUND_WELLS.slice(0, ACTIVE_COMPOUND_COUNT);
  const allCompoundWells = activeCompoundWellsByGroup.flat();
  const tem1Wells = [...POSITIVE_WELLS, ...VEHICLE_WELLS, ...allCompoundWells];
  const vehicleAdditionWells = [...NEGATIVE_WELLS, ...VEHICLE_WELLS];
  const allWells = [...POSITIVE_WELLS, ...NEGATIVE_WELLS, ...VEHICLE_WELLS, ...allCompoundWells];
  const activeCompounds = compounds.slice(0, ACTIVE_COMPOUND_COUNT);
  const enzymeVolume = 20;
  const compoundVolume = 5;
  const nitrocefinVolume = 25;
  const workingPlate = "wellplate_pcr_parts_4";
  const positiveDestWell = "A1";
  const vehicleDestWell = "A2";
  const deckRows = [
    { source: "TEM-1 stock", location: `${sourceBlock} / hole_1`, serves: "TEM-1 dilution prep", needed: 2, overage: 2 },
    { source: "BLB tube 1", location: `${sourceBlock} / ${blbAnchor}`, serves: "compound/control working solutions + T1262 intermediate", needed: (ACTIVE_COMPOUND_COUNT + 1) * 47.5 + 49, overage: sourceOverage },
    { source: "BLB tube 2", location: `${sourceBlock} / ${noEnzymeAnchor}`, serves: "TEM-1 dilution + vehicle + no-enzyme wells", needed: 198 + 900 + 95 + NEGATIVE_WELLS.length * enzymeVolume, overage: sourceOverage },
    { source: "DMSO", location: `${sourceBlock} / hole_9`, serves: "matched vehicle prep", needed: 5, overage: 5 },
    { source: "Raw compound/control stocks", location: "source wells below", serves: "working plate prep (T1262 uses 1 uL serial dilution)", needed: (ACTIVE_COMPOUND_COUNT + 1) * 2.5 - 1.5, overage: compoundOverage },
    { source: "TEM-1 working", location: `${sourceBlock} / ${enzymeAnchor}`, serves: csv(tem1Wells), needed: tem1Wells.length * enzymeVolume, overage: 0 },
    { source: "Vehicle working", location: `${workingPlate} / ${vehicleDestWell}`, serves: csv(vehicleAdditionWells), needed: vehicleAdditionWells.length * compoundVolume, overage: 0 },
    { source: "Positive control working", location: `${workingPlate} / ${positiveDestWell}`, serves: csv(POSITIVE_WELLS), needed: POSITIVE_WELLS.length * compoundVolume, overage: 0 },
    ...activeCompounds.map((c, i) => ({
      source: `Compound ${i + 1}: ${c.label}`,
      location: `${workingPlate} / A${i + 3}`,
      serves: csv(COMPOUND_WELLS[i]),
      needed: COMPOUND_WELLS[i].length * compoundVolume,
      overage: 0,
    })),
    { source: "Nitrocefin stock", location: `${sourceBlock} / ${nitrocefinStockAnchor}`, serves: "just-in-time nitrocefin prep", needed: 6.25, overage: 2 },
    { source: "Nitrocefin BLB", location: `${sourceBlock} / ${nitrocefinBlbAnchor}`, serves: "just-in-time nitrocefin prep", needed: 1243.75, overage: 50 },
    { source: "2x nitrocefin working", location: `${sourceBlock} / ${nitrocefinAnchor}`, serves: csv(allWells), needed: allWells.length * nitrocefinVolume, overage: nitrocefinOverage },
  ];
  const wellRows = [
    ...POSITIVE_WELLS.map((well) => ({ well, condition: "Positive control", prep: "TEM-1", prepVol: enzymeVolume, addition: "Clavulanic acid", addVol: compoundVolume })),
    ...NEGATIVE_WELLS.map((well) => ({ well, condition: "No-TEM-1 control", prep: "No-enzyme", prepVol: enzymeVolume, addition: "Vehicle / BLB", addVol: compoundVolume })),
    ...VEHICLE_WELLS.map((well) => ({ well, condition: "Vehicle + TEM-1", prep: "TEM-1", prepVol: enzymeVolume, addition: "Vehicle / BLB", addVol: compoundVolume })),
    ...activeCompounds.flatMap((c, i) => COMPOUND_WELLS[i].map((well) => ({ well, condition: `Compound ${i + 1}`, prep: "TEM-1", prepVol: enzymeVolume, addition: c.label, addVol: compoundVolume }))),
  ].map((r) => ({ ...r, nitrocefinVol: nitrocefinVolume, total: r.prepVol + r.addVol + nitrocefinVolume }));

  const values = {
    pipette, tipbox, source_block: sourceBlock, assay_plate: assayPlate, plate_home: plateHome, shaker, shaker_slot: shakerSlot,
    working_plate: workingPlate, blb_source: sourceBlock, dmso_source: sourceBlock, tem1_stock_source: sourceBlock,
    blb_anchor: blbAnchor, blb_anchor_2: noEnzymeAnchor, dmso_anchor: "hole_9", nitrocefin_blb_anchor: nitrocefinBlbAnchor, nitrocefin_stock_anchor: nitrocefinStockAnchor, tem1_stock_anchor: "hole_1", tem1_intermediate_anchor: "hole_2", tem1_working_anchor: enzymeAnchor,
    nitrocefin_anchor: nitrocefinAnchor,
    positive_source_plate: positivePlate, positive_source_well: upper(positiveWell), positive_dest_well: positiveDestWell, vehicle_dest_well: vehicleDestWell,
    positive_wells: csv(POSITIVE_WELLS), negative_wells: csv(NEGATIVE_WELLS),
    tem1_wells: csv(tem1Wells), vehicle_addition_wells: csv(vehicleAdditionWells),
    tem1_well_count: tem1Wells.length, negative_well_count: NEGATIVE_WELLS.length, vehicle_addition_count: vehicleAdditionWells.length,
    positive_well_count: POSITIVE_WELLS.length, replicate_count: 3,
    enzyme_volume_ul: enzymeVolume, compound_volume_ul: compoundVolume, nitrocefin_volume_ul: nitrocefinVolume,
    stock_volume_ul: 2.5, compound_blb_volume_ul: 47.5, vehicle_dmso_volume_ul: 5, vehicle_blb_volume_ul: 95, nitrocefin_stock_volume_ul: 6.25, nitrocefin_blb_volume_ul: 1243.75, nitrocefin_mix_volume_ul: 100,
    tem1_stock_volume_ul: 2, tem1_step1_blb_volume_ul: 198, tem1_intermediate_volume_ul: 100, tem1_step2_blb_volume_ul: 900, tem1_mix_volume_ul: 100, mix_volume_ul: 10, mix_cycles: 5,
    plate_mix_minutes: plateMixMin, preincubation_minutes: waitMin,
    run_name: runName.trim() || "tem1_activity_screen",
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
    if (!pipette || !tipbox || !sourceBlock || !assayPlate || !plateHome || !shaker) e.push("Select all required world objects.");
    if (!(plateMixMin >= 0)) e.push("Plate mix time must be zero or positive.");
    if (!(waitMin >= 0)) e.push("Pre-incubation time must be zero or positive.");
    if (sourceOverage < 0 || compoundOverage < 0 || nitrocefinOverage < 0) e.push("Deck-loading overage values must be zero or positive.");
    const wellRe = /^[A-H](?:[1-9]|1[0-2])$/;
    if (!wellRe.test(upper(positiveWell))) e.push("Positive-control source well must be A1-H12.");
    activeCompounds.forEach((c, i) => {
      if (!c.plate) e.push(`Select a source plate for compound ${i + 1}.`);
      if (!wellRe.test(upper(c.well))) e.push(`Compound ${i + 1} source well must be A1-H12.`);
    });
    const usedHoles = [enzymeAnchor, noEnzymeAnchor, blbAnchor, nitrocefinAnchor, nitrocefinBlbAnchor, nitrocefinStockAnchor, "hole_1", "hole_2", "hole_9"];
    if (new Set(usedHoles).size !== usedHoles.length) e.push("Use separate cold-block holes for enzyme, BLB, DMSO, nitrocefin stock, and nitrocefin working solution.");
    return e;
  }
  const errors = [...localErrors(), ...hostErrors];
  const confirmed = snapshot !== null && snapshot === live && errors.length === 0;

  useEffect(() => zeon.onValidationErrors((errs) => setHostErrors(errs.map((e) => `${e.path}: ${e.message}`))), []);
  useEffect(() => { zeon.setConfirmed?.(confirmed); }, [confirmed]);
  useEffect(() => { zeon.setDirty?.(!confirmed); }, [confirmed]);

  const selectObj = (value: string, set: (v: string) => void, opts: Obj[]) => (
    <select style={STYLE.field} value={value} onChange={(e) => set(e.target.value)}>
      {opts.map((o) => <option key={o.uuid} value={objName(o)}>{objName(o)}</option>)}
    </select>
  );
  const holeSelect = (value: string, set: (v: string) => void) => (
    <select style={STYLE.field} value={value} onChange={(e) => set(e.target.value)}>
      {HOLES.map((h) => <option key={h} value={h}>{h}</option>)}
    </select>
  );
  const updateCompound = (i: number, patch: Partial<Compound>) => setCompounds((xs) => xs.map((c, j) => j === i ? { ...c, ...patch } : c));
  const chip = (text: string, kind: string) => <span style={{ ...STYLE.chip, background: COLORS[kind] }}>{text}</span>;

  return (
    <div style={STYLE.page}>
      <div style={STYLE.content}>
        <div style={STYLE.eyebrow}>TEM-1 beta-lactamase · nitrocefin activity screen</div>
        <h1 style={STYLE.h1}>Single-Plate Activity Screen</h1>
        <p style={STYLE.sub}>
          Builds the R3 v1 column-strip 30-well plate: 6 QC controls and 8 test compounds in triplicate, with edge wells left empty.
        </p>

        <h2 style={STYLE.h2}>Run Timing</h2>
        <div style={STYLE.grid2}>
          <div><label style={STYLE.label}>Plate mix minutes</label><input style={STYLE.field} type="number" min={0} step={0.25} value={plateMixMin} onChange={(e) => setPlateMixMin(Number(e.target.value))} /></div>
          <div><label style={STYLE.label}>Pre-incubation minutes</label><input style={STYLE.field} type="number" min={0} step={0.5} value={waitMin} onChange={(e) => setWaitMin(Number(e.target.value))} /></div>
          <div><label style={STYLE.label}>Run name</label><input style={STYLE.field} value={runName} onChange={(e) => setRunName(e.target.value)} /></div>
        </div>
        <p style={STYLE.sub}>
          The robot stops after nitrocefin addition and run-log capture. Move the plate to the reader manually and start the A490 method from Gen5.
        </p>
        <p style={STYLE.sub}>
          Nitrocefin is added in a stagger-aware order: no-TEM-1 controls first, then clavulanate and inhibitor-class compounds, then substrate-control compounds, with the vehicle + TEM-1 max-activity wells last. The run-log completion time for each nitrocefin batch is that condition's t0 for analysis.
        </p>

        <h2 style={STYLE.h2}>Deck Objects</h2>
        <div style={STYLE.grid2}>
          <div><label style={STYLE.label}>Starting pipette</label>{selectObj(pipette, setPipette, objectOptions(["epipette_10ul", "epipette_120ul"]))}</div>
          <div><label style={STYLE.label}>Starting tip box</label>{selectObj(tipbox, setTipbox, objectOptions(["tipbox_10ul", "tipbox_120ul"]))}</div>
          <div><label style={STYLE.label}>Reagent cold block</label>{selectObj(sourceBlock, setSourceBlock, objectOptions(["coldblock_wellplate", "coldblock_large", "coldblock_small"]))}</div>
          <div><label style={STYLE.label}>Assay plate</label>{selectObj(assayPlate, setAssayPlate, objectOptions(["wellplate_96_flatbottom"]))}</div>
          <div><label style={STYLE.label}>Plate home</label>{selectObj(plateHome, setPlateHome, objectOptions(["wellplate_holder_tags", "wellplate_holder_fixture_plate", "plate_stand_holder"]))}</div>
          <div><label style={STYLE.label}>Plate shaker</label>{selectObj(shaker, setShaker, objectOptions(["wellplate_shaker"]))}</div>
          <div><label style={STYLE.label}>Shaker slot</label><select style={STYLE.field} value={shakerSlot} onChange={(e) => setShakerSlot(e.target.value)}>{["slot_1", "slot_2", "slot_3", "slot_4"].map((s) => <option key={s} value={s}>{s}</option>)}</select></div>
        </div>

        <h2 style={STYLE.h2}>Cold-Block Reagents</h2>
        <div style={STYLE.grid4}>
          <div><label style={STYLE.label}>TEM-1 prep</label>{holeSelect(enzymeAnchor, setEnzymeAnchor)}</div>
          <div><label style={STYLE.label}>No-enzyme prep</label>{holeSelect(noEnzymeAnchor, setNoEnzymeAnchor)}</div>
          <div><label style={STYLE.label}>BLB tube 1</label>{holeSelect(blbAnchor, setBlbAnchor)}</div>
          <div><label style={STYLE.label}>Nitrocefin BLB</label>{holeSelect(nitrocefinBlbAnchor, setNitrocefinBlbAnchor)}</div>
          <div><label style={STYLE.label}>Nitrocefin stock</label>{holeSelect(nitrocefinStockAnchor, setNitrocefinStockAnchor)}</div>
          <div><label style={STYLE.label}>2x nitrocefin</label>{holeSelect(nitrocefinAnchor, setNitrocefinAnchor)}</div>
        </div>

        <h2 style={STYLE.h2}>Source Compounds</h2>
        <div style={STYLE.card}>
          <table style={STYLE.table}>
            <thead><tr><th style={STYLE.th}>Condition</th><th style={STYLE.th}>Destination wells</th><th style={STYLE.th}>Source plate</th><th style={STYLE.th}>Source well</th></tr></thead>
            <tbody>
              <tr><td style={STYLE.td}>Positive control: clavulanic acid</td><td style={STYLE.td}>{csv(POSITIVE_WELLS)}</td><td style={STYLE.td}>{selectObj(positivePlate, setPositivePlate, sourcePlates)}</td><td style={STYLE.td}><input style={STYLE.field} value={positiveWell} onChange={(e) => setPositiveWell(e.target.value)} /></td></tr>
              {activeCompounds.map((c, i) => (
                <tr key={i}>
                  <td style={STYLE.td}>Compound {i + 1}: {c.label}</td>
                  <td style={STYLE.td}>{csv(COMPOUND_WELLS[i])}</td>
                  <td style={STYLE.td}>{selectObj(c.plate, (v) => updateCompound(i, { plate: v }), sourcePlates)}</td>
                  <td style={STYLE.td}><input style={STYLE.field} value={c.well} onChange={(e) => updateCompound(i, { well: e.target.value })} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 style={STYLE.h2}>Deck Loading Volumes</h2>
        <p style={STYLE.sub}>
          Use this table to load enough liquid onto the deck before the run. Transfer needed is what the robot will aspirate; recommended load adds dead-volume overage.
        </p>
        <div style={STYLE.grid4}>
          <div><label style={STYLE.label}>Cold-block overage</label><input style={STYLE.field} type="number" min={0} step={5} value={sourceOverage} onChange={(e) => setSourceOverage(Number(e.target.value))} /></div>
          <div><label style={STYLE.label}>Compound overage</label><input style={STYLE.field} type="number" min={0} step={1} value={compoundOverage} onChange={(e) => setCompoundOverage(Number(e.target.value))} /></div>
          <div><label style={STYLE.label}>Nitrocefin overage</label><input style={STYLE.field} type="number" min={0} step={5} value={nitrocefinOverage} onChange={(e) => setNitrocefinOverage(Number(e.target.value))} /></div>
        </div>
        <div style={STYLE.card}>
          <table style={STYLE.table}>
            <thead>
              <tr><th style={STYLE.th}>Source</th><th style={STYLE.th}>Deck location</th><th style={STYLE.th}>Destination wells</th><th style={STYLE.th}>Transfer needed</th><th style={STYLE.th}>Load at least</th></tr>
            </thead>
            <tbody>
              {deckRows.map((r) => (
                <tr key={r.source}>
                  <td style={STYLE.td}>{r.source}</td>
                  <td style={STYLE.td}>{r.location}</td>
                  <td style={STYLE.td}>{r.serves}</td>
                  <td style={STYLE.td}>{ul(r.needed)}</td>
                  <td style={{ ...STYLE.td, fontWeight: 800 }}>{ul(r.needed + r.overage)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 style={STYLE.h2}>Plate Layout</h2>
        <div style={STYLE.card}>
          <p style={STYLE.sub}>
            {chip("Positive", "positive")} {csv(POSITIVE_WELLS)} · {chip("No TEM-1", "negative")} {csv(NEGATIVE_WELLS)} · {chip("8 test compounds", "compound")} {allCompoundWells.length} wells
          </p>
          <table style={STYLE.table}>
            <tbody>
              {["A", "B", "C", "D", "E", "F", "G", "H"].map((row) => (
                <tr key={row as string}>
                  {Array.from({ length: 12 }, (_, i) => `${row}${i + 1}`).map((w) => {
                    const kind = POSITIVE_WELLS.includes(w) ? "positive" : NEGATIVE_WELLS.includes(w) ? "negative" : VEHICLE_WELLS.includes(w) ? "vehicle" : allCompoundWells.includes(w) ? "compound" : "";
                    return <td key={w} style={{ ...STYLE.td, width: "8.3%", color: kind ? COLORS[kind] : MUTED, fontFamily: MONO, fontWeight: kind ? 800 : 400 }}>{w}</td>;
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p style={{ ...STYLE.sub, marginTop: 10 }}>
            Per well: 20 uL enzyme/no-enzyme prep + 5 uL compound/control + 25 uL nitrocefin = 50 uL. The workflow batches repeated additions: up to 5 wells per 100 uL enzyme aspiration, 4 wells per 100 uL nitrocefin aspiration, and 2 wells per 10 uL compound/control aspiration.
          </p>
        </div>

        <h2 style={STYLE.h2}>Per-Well Volumes</h2>
        <div style={STYLE.card}>
          <table style={STYLE.table}>
            <thead>
              <tr><th style={STYLE.th}>Well</th><th style={STYLE.th}>Condition</th><th style={STYLE.th}>Prep</th><th style={STYLE.th}>Compound/control</th><th style={STYLE.th}>Nitrocefin</th><th style={STYLE.th}>Final</th></tr>
            </thead>
            <tbody>
              {wellRows.map((r) => (
                <tr key={r.well}>
                  <td style={STYLE.td}>{r.well}</td>
                  <td style={STYLE.td}>{r.condition}</td>
                  <td style={STYLE.td}>{r.prep}: {ul(r.prepVol)}</td>
                  <td style={STYLE.td}>{r.addition}: {ul(r.addVol)}</td>
                  <td style={STYLE.td}>{ul(r.nitrocefinVol)}</td>
                  <td style={{ ...STYLE.td, fontWeight: r.total === 50 ? 800 : 400, color: r.total === 50 ? INK : "#b91c1c" }}>{ul(r.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {errors.length > 0 && <div style={STYLE.error}>{errors.map((e, i) => <div key={i}>- {e}</div>)}</div>}

        <button type="button" style={STYLE.button} onClick={() => { const e = localErrors(); setHostErrors([]); if (e.length === 0) { zeon.submit(values); setSnapshot(live); } }}>
          {confirmed ? "Setup confirmed" : `Confirm 36-well screen (${waitMin || 0} min pre-incubation)`}
        </button>
      </div>
    </div>
  );
}
