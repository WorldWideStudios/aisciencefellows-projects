import React, { useEffect, useState } from "react";

declare const zeon: {
  schema: { name: string; type: string; description?: string; defaultValue?: unknown }[];
  worldObjects: { uuid: string; name: string; displayName?: string; meshType?: string }[];
  defaults: Record<string, unknown>;
  submit: (values: Record<string, unknown>) => void;
  setConfirmed?: (ok: boolean) => void;
  setDirty?: (dirty: boolean) => void;
  onValidationErrors: (cb: (errs: { path: string; message: string }[]) => void) => void;
};

type Obj = { uuid: string; name: string; displayName?: string; meshType?: string };
type Item = { label: string; plate: string; sourceWell: string; destWell: string };

const SANS = "system-ui, -apple-system, Segoe UI, sans-serif";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
const INK = "#1f2933", MUTED = "#62707f", LINE = "#e5e7eb", BG = "#f8fafc";
const S: Record<string, React.CSSProperties> = {
  page: { fontFamily: SANS, color: INK, background: BG, minHeight: "100vh", padding: "30px 24px 44px", boxSizing: "border-box" },
  content: { maxWidth: 920, margin: "0 auto" },
  eyebrow: { fontFamily: MONO, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: MUTED, marginBottom: 10 },
  h1: { fontSize: 28, lineHeight: 1.05, letterSpacing: -0.6, margin: "0 0 10px" },
  sub: { color: MUTED, fontSize: 13.5, lineHeight: 1.55, margin: "0 0 18px" },
  h2: { fontFamily: MONO, fontSize: 11, letterSpacing: 1, textTransform: "uppercase", borderTop: `1px solid ${LINE}`, paddingTop: 18, margin: "28px 0 10px" },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 14px" },
  grid4: { display: "grid", gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 6 },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, color: MUTED, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 5 },
  field: { width: "100%", boxSizing: "border-box", border: `1px solid ${LINE}`, borderRadius: 8, padding: "8px 10px", background: "#fff", color: INK, fontSize: 13.5 },
  card: { border: `1px solid ${LINE}`, borderRadius: 10, padding: 14, background: "#fff", marginTop: 12 },
  table: { width: "100%", borderCollapse: "collapse", fontSize: 12.5 },
  th: { fontFamily: MONO, textAlign: "left", color: MUTED, borderBottom: `1px solid ${LINE}`, padding: "7px 6px", fontSize: 10.5, textTransform: "uppercase", letterSpacing: 0.4 },
  td: { borderBottom: `1px solid ${LINE}`, padding: "7px 6px", verticalAlign: "top" },
  error: { background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", padding: "10px 12px", borderRadius: 8, fontSize: 13, marginTop: 14 },
  button: { width: "100%", marginTop: 18, padding: "13px 16px", border: "none", borderRadius: 9, background: "#0f766e", color: "#fff", fontWeight: 800, cursor: "pointer", fontSize: 14.5 },
};

const DEFAULT_ITEMS = [
  ["T1262 Tazobactam (1 uM assay)", "wellplate_pcr_parts_1", "B10", "A3"],
  ["T6685 Sulbactam sodium", "wellplate_pcr_parts_1", "F2", "A4"],
  ["T14081 Enmetazobactam", "wellplate_pcr_parts_1", "F7", "A5"],
  ["T1008 Cephalexin", "wellplate_pcr_parts_1", "A9", "A6"],
  ["T0224 Meropenem", "wellplate_pcr_parts_2", "A3", "A7"],
  ["T0985 Oxacillin sodium salt", "wellplate_pcr_parts_2", "A4", "A8"],
  ["T0138 Cefpiramide acid", "wellplate_pcr_parts_1", "A2", "A9"],
  ["T8390 Cefazolin", "wellplate_pcr_parts_1", "F3", "A10"],
] as const;

const objName = (o: Obj) => o.displayName || o.name || o.uuid;
const ul = (n: number) => `${Math.round(n * 10) / 10} uL`;
const upper = (s: string) => s.trim().toUpperCase();

export default function Tem1DilutionPlate() {
  const schemaDefault = (name: string, fallback: unknown) => zeon.schema.find((s) => s.name === name)?.defaultValue ?? fallback;
  const initial = (name: string, fallback: unknown) => zeon.defaults[name] ?? schemaDefault(name, fallback);
  const byType = (types: string[]) => zeon.worldObjects.filter((o) => o.meshType !== undefined && types.includes(o.meshType));
  const objectOptions = (types: string[]) => byType(types).length ? byType(types) : zeon.worldObjects;
  const firstName = (types: string[], fallback: string) => objectOptions(types)[0] ? objName(objectOptions(types)[0]) : fallback;

  const [pipette, setPipette] = useState(String(initial("pipette", "epipette_10ul")));
  const [tipbox, setTipbox] = useState(String(initial("tipbox", "tipbox_10ul_1")));
  const [blbSource, setBlbSource] = useState(String(initial("blb_source", "coldblock_wellplate")));
  const [dmsoSource, setDmsoSource] = useState(String(initial("dmso_source", "coldblock_wellplate")));
  const [workingPlate, setWorkingPlate] = useState(String(initial("working_plate", "wellplate_pcr_parts_4")));
  const [tem1StockSource, setTem1StockSource] = useState(String(initial("tem1_stock_source", "coldblock_wellplate")));
  const [blbAnchor, setBlbAnchor] = useState(String(initial("blb_anchor", "hole_5")));
  const [blbAnchor2, setBlbAnchor2] = useState(String(initial("blb_anchor_2", "hole_6")));
  const [dmsoAnchor, setDmsoAnchor] = useState(String(initial("dmso_anchor", "hole_9")));
  const [tem1StockAnchor, setTem1StockAnchor] = useState(String(initial("tem1_stock_anchor", "hole_1")));
  const [tem1IntermediateAnchor, setTem1IntermediateAnchor] = useState(String(initial("tem1_intermediate_anchor", "hole_2")));
  const [tem1WorkingAnchor, setTem1WorkingAnchor] = useState(String(initial("tem1_working_anchor", "hole_8")));
  const [positivePlate, setPositivePlate] = useState(String(initial("positive_source_plate", "wellplate_pcr_parts_1")));
  const [positiveWell, setPositiveWell] = useState(String(initial("positive_source_well", "H7")));
  const [positiveDest, setPositiveDest] = useState(String(initial("positive_dest_well", "A1")));
  const [vehicleDest, setVehicleDest] = useState(String(initial("vehicle_dest_well", "A2")));
  const [stockVol, setStockVol] = useState(Number(initial("stock_volume_ul", 2.5)));
  const [compoundBlbVol, setCompoundBlbVol] = useState(Number(initial("compound_blb_volume_ul", 47.5)));
  const [vehicleDmsoVol, setVehicleDmsoVol] = useState(Number(initial("vehicle_dmso_volume_ul", 5)));
  const [vehicleBlbVol, setVehicleBlbVol] = useState(Number(initial("vehicle_blb_volume_ul", 95)));
  const [tem1StockVol, setTem1StockVol] = useState(Number(initial("tem1_stock_volume_ul", 2)));
  const [tem1Step1BlbVol, setTem1Step1BlbVol] = useState(Number(initial("tem1_step1_blb_volume_ul", 198)));
  const [tem1IntermediateVol, setTem1IntermediateVol] = useState(Number(initial("tem1_intermediate_volume_ul", 100)));
  const [tem1Step2BlbVol, setTem1Step2BlbVol] = useState(Number(initial("tem1_step2_blb_volume_ul", 900)));
  const [tem1MixVol, setTem1MixVol] = useState(Number(initial("tem1_mix_volume_ul", 100)));
  const [mixVol, setMixVol] = useState(Number(initial("mix_volume_ul", 10)));
  const [mixCycles, setMixCycles] = useState(Number(initial("mix_cycles", 5)));
  const [items, setItems] = useState<Item[]>(() => DEFAULT_ITEMS.map((d, i) => ({
    label: d[0],
    plate: String(initial(`compound_${i + 1}_source_plate`, d[1])),
    sourceWell: String(initial(`compound_${i + 1}_source_well`, d[2])),
    destWell: String(initial(`compound_${i + 1}_dest_well`, d[3])),
  })));
  const [hostErrors, setHostErrors] = useState<string[]>([]);
  const [snapshot, setSnapshot] = useState<string | null>(null);

  const pcrPlates = objectOptions(["wellplate_pcr"]);
  const coldBlocks = objectOptions(["coldblock_wellplate", "coldblock_large", "coldblock_small"]);
  const stockWorkingTotal = stockVol + compoundBlbVol;
  const vehicleTotal = vehicleDmsoVol + vehicleBlbVol;
  const workingUM = stockWorkingTotal > 0 ? 10000 * stockVol / stockWorkingTotal : 0;
  const finalAssayUM = workingUM * 5 / 50;
  const vehiclePct = vehicleTotal > 0 ? 100 * vehicleDmsoVol / vehicleTotal : 0;
  const blbTube1Needed = items.length * compoundBlbVol + compoundBlbVol;
  const blbTube2Needed = vehicleBlbVol + tem1Step1BlbVol + tem1Step2BlbVol;
  const blbNeeded = blbTube1Needed + blbTube2Needed;
  const stockNeeded = stockVol;
  const dmsoNeeded = vehicleDmsoVol;

  const values = {
    pipette, tipbox, blb_source: blbSource, dmso_source: dmsoSource, working_plate: workingPlate, tem1_stock_source: tem1StockSource,
    blb_anchor: blbAnchor, blb_anchor_2: blbAnchor2, dmso_anchor: dmsoAnchor, tem1_stock_anchor: tem1StockAnchor, tem1_intermediate_anchor: tem1IntermediateAnchor, tem1_working_anchor: tem1WorkingAnchor,
    positive_source_plate: positivePlate, positive_source_well: upper(positiveWell), positive_dest_well: upper(positiveDest), vehicle_dest_well: upper(vehicleDest),
    stock_volume_ul: stockVol, compound_blb_volume_ul: compoundBlbVol, vehicle_dmso_volume_ul: vehicleDmsoVol, vehicle_blb_volume_ul: vehicleBlbVol,
    tem1_stock_volume_ul: tem1StockVol, tem1_step1_blb_volume_ul: tem1Step1BlbVol, tem1_intermediate_volume_ul: tem1IntermediateVol, tem1_step2_blb_volume_ul: tem1Step2BlbVol, tem1_mix_volume_ul: tem1MixVol,
    mix_volume_ul: mixVol, mix_cycles: Math.round(mixCycles),
    ...Object.fromEntries(items.flatMap((it, i) => [
      [`compound_${i + 1}_source_plate`, it.plate], [`compound_${i + 1}_source_well`, upper(it.sourceWell)], [`compound_${i + 1}_dest_well`, upper(it.destWell)],
    ])),
  };
  const live = JSON.stringify(values);

  function localErrors() {
    const e: string[] = [];
    const wellRe = /^[A-H](?:[1-9]|1[0-2])$/;
    [positiveWell, positiveDest, vehicleDest, ...items.flatMap((it) => [it.sourceWell, it.destWell])].forEach((w) => {
      if (!wellRe.test(upper(w))) e.push(`Invalid well: ${w}`);
    });
    const dests = [upper(positiveDest), upper(vehicleDest), ...items.map((it) => upper(it.destWell))];
    if (new Set(dests).size !== dests.length) e.push("Working-plate destination wells must be unique.");
    if (stockVol <= 0 || compoundBlbVol <= 0 || vehicleDmsoVol <= 0 || vehicleBlbVol <= 0) e.push("Dilution volumes must be positive.");
    if (tem1StockVol <= 0 || tem1Step1BlbVol <= 0 || tem1IntermediateVol <= 0 || tem1Step2BlbVol <= 0 || tem1MixVol <= 0) e.push("TEM-1 dilution volumes must be positive.");
    if (new Set([blbAnchor, blbAnchor2, dmsoAnchor, tem1StockAnchor, tem1IntermediateAnchor, tem1WorkingAnchor].map(upper)).size !== 6) e.push("Cold-block anchors for BLB, DMSO, and TEM-1 dilution tubes must be unique.");
    if (mixVol <= 0 || mixCycles < 1) e.push("Mix volume must be positive and mix cycles must be at least 1.");
    return e;
  }
  const errors = [...localErrors(), ...hostErrors];
  const confirmed = snapshot !== null && snapshot === live && errors.length === 0;

  useEffect(() => zeon.onValidationErrors((errs) => setHostErrors(errs.map((e) => `${e.path}: ${e.message}`))), []);
  useEffect(() => { zeon.setConfirmed?.(confirmed); }, [confirmed]);
  useEffect(() => { zeon.setDirty?.(!confirmed); }, [confirmed]);

  const selectObj = (value: string, set: (v: string) => void, opts: Obj[]) => (
    <select style={S.field} value={value} onChange={(e) => set(e.target.value)}>{opts.map((o) => <option key={o.uuid} value={objName(o)}>{objName(o)}</option>)}</select>
  );
  const updateItem = (i: number, patch: Partial<Item>) => setItems((xs) => xs.map((x, j) => j === i ? { ...x, ...patch } : x));

  return (
    <div style={S.page}>
      <div style={S.content}>
        <div style={S.eyebrow}>TEM-1 beta-lactamase · working-solution prep</div>
        <h1 style={S.h1}>Dilution Plate</h1>
        <p style={S.sub}>Prepares working solutions for the 8 R3 v1 compounds plus clavulanate control, and a 5% DMSO matched vehicle on the fourth PCR plate.</p>

        <h2 style={S.h2}>Deck Objects</h2>
        <div style={S.grid2}>
          <div><label style={S.label}>Starting pipette</label>{selectObj(pipette, setPipette, objectOptions(["epipette_10ul", "epipette_120ul"]))}</div>
          <div><label style={S.label}>Starting tip box</label>{selectObj(tipbox, setTipbox, objectOptions(["tipbox_10ul", "tipbox_120ul"]))}</div>
          <div><label style={S.label}>BLB source</label>{selectObj(blbSource, setBlbSource, coldBlocks)}</div>
          <div><label style={S.label}>DMSO source</label>{selectObj(dmsoSource, setDmsoSource, coldBlocks)}</div>
          <div><label style={S.label}>Working plate</label>{selectObj(workingPlate, setWorkingPlate, pcrPlates)}</div>
          <div><label style={S.label}>TEM-1 stock source</label>{selectObj(tem1StockSource, setTem1StockSource, coldBlocks)}</div>
        </div>
        <div style={{ ...S.grid4, marginTop: 10 }}>
          <div><label style={S.label}>BLB tube 1 anchor</label><input style={S.field} value={blbAnchor} onChange={(e) => setBlbAnchor(e.target.value)} /></div>
          <div><label style={S.label}>BLB tube 2 anchor</label><input style={S.field} value={blbAnchor2} onChange={(e) => setBlbAnchor2(e.target.value)} /></div>
          <div><label style={S.label}>DMSO anchor</label><input style={S.field} value={dmsoAnchor} onChange={(e) => setDmsoAnchor(e.target.value)} /></div>
          <div><label style={S.label}>TEM-1 stock anchor</label><input style={S.field} value={tem1StockAnchor} onChange={(e) => setTem1StockAnchor(e.target.value)} /></div>
          <div><label style={S.label}>TEM-1 intermediate</label><input style={S.field} value={tem1IntermediateAnchor} onChange={(e) => setTem1IntermediateAnchor(e.target.value)} /></div>
          <div><label style={S.label}>TEM-1 working</label><input style={S.field} value={tem1WorkingAnchor} onChange={(e) => setTem1WorkingAnchor(e.target.value)} /></div>
        </div>

        <h2 style={S.h2}>TEM-1 Dilution</h2>
        <div style={S.grid4}>
          <div><label style={S.label}>TEM-1 stock</label><input style={S.field} type="number" step={0.1} value={tem1StockVol} onChange={(e) => setTem1StockVol(Number(e.target.value))} /></div>
          <div><label style={S.label}>Step 1 BLB</label><input style={S.field} type="number" step={1} value={tem1Step1BlbVol} onChange={(e) => setTem1Step1BlbVol(Number(e.target.value))} /></div>
          <div><label style={S.label}>Intermediate</label><input style={S.field} type="number" step={1} value={tem1IntermediateVol} onChange={(e) => setTem1IntermediateVol(Number(e.target.value))} /></div>
          <div><label style={S.label}>Step 2 BLB</label><input style={S.field} type="number" step={1} value={tem1Step2BlbVol} onChange={(e) => setTem1Step2BlbVol(Number(e.target.value))} /></div>
          <div><label style={S.label}>TEM mix volume</label><input style={S.field} type="number" step={5} value={tem1MixVol} onChange={(e) => setTem1MixVol(Number(e.target.value))} /></div>
        </div>
        <div style={S.card}>
          <p style={S.sub}>Step 1: {ul(tem1StockVol)} of 100 ng/uL TEM-1 + {ul(tem1Step1BlbVol)} BLB in {tem1IntermediateAnchor} = {ul(tem1StockVol + tem1Step1BlbVol)} at ~1 ng/uL.</p>
          <p style={S.sub}>Step 2: {ul(tem1IntermediateVol)} intermediate + {ul(tem1Step2BlbVol)} BLB in {tem1WorkingAnchor} = {ul(tem1IntermediateVol + tem1Step2BlbVol)} at ~0.1 ng/uL, enough for {Math.floor((tem1IntermediateVol + tem1Step2BlbVol) / 20)} assay wells at 20 uL/well.</p>
        </div>

        <h2 style={S.h2}>Dilution Math</h2>
        <div style={S.grid4}>
          <div><label style={S.label}>Stock volume</label><input style={S.field} type="number" step={0.1} value={stockVol} onChange={(e) => setStockVol(Number(e.target.value))} /></div>
          <div><label style={S.label}>Compound BLB</label><input style={S.field} type="number" step={0.1} value={compoundBlbVol} onChange={(e) => setCompoundBlbVol(Number(e.target.value))} /></div>
          <div><label style={S.label}>Vehicle DMSO</label><input style={S.field} type="number" step={0.1} value={vehicleDmsoVol} onChange={(e) => setVehicleDmsoVol(Number(e.target.value))} /></div>
          <div><label style={S.label}>Vehicle BLB</label><input style={S.field} type="number" step={0.1} value={vehicleBlbVol} onChange={(e) => setVehicleBlbVol(Number(e.target.value))} /></div>
        </div>
        <div style={S.card}>
          <p style={S.sub}>Compound/control working solution: {ul(stockVol)} of 10 mM stock + {ul(compoundBlbVol)} BLB = {ul(stockWorkingTotal)} at {Math.round(workingUM)} uM. In the 50 uL assay, 5 uL gives {Math.round(finalAssayUM)} uM final.</p>
          <p style={S.sub}>Vehicle working solution: {ul(vehicleDmsoVol)} DMSO + {ul(vehicleBlbVol)} BLB = {ul(vehicleTotal)} at {Math.round(vehiclePct * 10) / 10}% DMSO.</p>
          <p style={S.sub}>Deck loading needed before overage: BLB total {ul(blbNeeded)} split as tube 1 ({blbAnchor}) {ul(blbTube1Needed)} and tube 2 ({blbAnchor2}) {ul(blbTube2Needed)}; TEM-1 stock {ul(tem1StockVol)}; DMSO {ul(dmsoNeeded)}; each compound/control stock {ul(stockNeeded)}.</p>
        </div>

        <h2 style={S.h2}>Working Plate Map</h2>
        <div style={S.card}>
          <table style={S.table}>
            <thead><tr><th style={S.th}>Working well</th><th style={S.th}>Solution</th><th style={S.th}>Source plate</th><th style={S.th}>Source well</th><th style={S.th}>Prepared volume</th></tr></thead>
            <tbody>
              <tr><td style={S.td}>{upper(positiveDest)}</td><td style={S.td}>T19860 Clavulanic Acid</td><td style={S.td}>{selectObj(positivePlate, setPositivePlate, pcrPlates)}</td><td style={S.td}><input style={S.field} value={positiveWell} onChange={(e) => setPositiveWell(e.target.value)} /></td><td style={S.td}>{ul(stockWorkingTotal)}</td></tr>
              <tr><td style={S.td}><input style={S.field} value={vehicleDest} onChange={(e) => setVehicleDest(e.target.value)} /></td><td style={S.td}>Matched vehicle</td><td style={S.td}>{dmsoSource}</td><td style={S.td}>{dmsoAnchor}</td><td style={S.td}>{ul(vehicleTotal)}</td></tr>
              {items.map((it, i) => (
                <tr key={i}>
                  <td style={S.td}><input style={S.field} value={it.destWell} onChange={(e) => updateItem(i, { destWell: e.target.value })} /></td>
                  <td style={S.td}>{it.label}</td>
                  <td style={S.td}>{selectObj(it.plate, (v) => updateItem(i, { plate: v }), pcrPlates)}</td>
                  <td style={S.td}><input style={S.field} value={it.sourceWell} onChange={(e) => updateItem(i, { sourceWell: e.target.value })} /></td>
                  <td style={S.td}>{ul(stockWorkingTotal)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h2 style={S.h2}>Mixing</h2>
        <div style={S.grid2}>
          <div><label style={S.label}>Mix volume</label><input style={S.field} type="number" step={0.5} value={mixVol} onChange={(e) => setMixVol(Number(e.target.value))} /></div>
          <div><label style={S.label}>Mix cycles</label><input style={S.field} type="number" step={1} value={mixCycles} onChange={(e) => setMixCycles(Number(e.target.value))} /></div>
        </div>

        {errors.length > 0 && <div style={S.error}>{errors.map((e, i) => <div key={i}>- {e}</div>)}</div>}
        <button type="button" style={S.button} onClick={() => { const e = localErrors(); setHostErrors([]); if (e.length === 0) { zeon.submit(values); setSnapshot(live); } }}>
          {confirmed ? "Setup confirmed" : "Confirm dilution plate setup"}
        </button>
      </div>
    </div>
  );
}
