import React, { useEffect, useMemo, useState } from "react";

declare const zeon: {
  schema: { name: string; type: string; description?: string; defaultValue?: unknown }[];
  worldObjects: { uuid: string; name: string; displayName?: string; meshType?: string }[];
  defaults: Record<string, unknown>;
  submit: (values: Record<string, unknown>) => void;
  setConfirmed?: (ok: boolean) => void;
  setDirty?: (dirty: boolean) => void;
  onValidationErrors: (cb: (errs: { path: string; message: string }[]) => void) => void;
};

const SANS = "system-ui, -apple-system, Segoe UI, sans-serif";
const MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace";
const INK = "#1f2933";
const MUTED = "#62707f";
const LINE = "#e5e7eb";
const BG = "#f0f9ff";

const STYLE: Record<string, React.CSSProperties> = {
  page: { fontFamily: SANS, color: INK, background: BG, minHeight: "100vh", padding: "28px 24px 40px", boxSizing: "border-box" },
  content: { maxWidth: 720, margin: "0 auto" },
  eyebrow: { fontFamily: MONO, fontSize: 11, letterSpacing: 1.2, textTransform: "uppercase", color: MUTED, marginBottom: 10 },
  h1: { fontSize: 26, lineHeight: 1.1, margin: "0 0 10px" },
  sub: { color: MUTED, fontSize: 13.5, lineHeight: 1.55, margin: "0 0 18px" },
  card: { border: `1px solid ${LINE}`, borderRadius: 10, padding: 14, background: "#fff", marginTop: 12 },
  grid2: { display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px 14px" },
  label: { display: "block", fontFamily: MONO, fontSize: 10.5, color: MUTED, textTransform: "uppercase", letterSpacing: 0.5, marginBottom: 5 },
  field: { width: "100%", boxSizing: "border-box", border: `1px solid ${LINE}`, borderRadius: 8, padding: "8px 10px", background: "#fff", color: INK, fontSize: 13.5 },
  statGrid: { display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 8, marginTop: 8 },
  stat: { border: `1px solid ${LINE}`, borderRadius: 8, padding: "10px 12px", background: "#f8fafc" },
  statLabel: { fontFamily: MONO, fontSize: 10, color: MUTED, textTransform: "uppercase", letterSpacing: 0.4 },
  statValue: { fontSize: 18, fontWeight: 700, marginTop: 4 },
  button: { width: "100%", marginTop: 18, padding: "13px 16px", border: "none", borderRadius: 9, background: "#0369a1", color: "#fff", fontWeight: 700, cursor: "pointer", fontSize: 14.5 },
  note: { fontSize: 12.5, color: MUTED, lineHeight: 1.55, marginTop: 10 },
};

type Obj = { uuid: string; name: string; displayName?: string; meshType?: string };

const objName = (o: Obj) => o.displayName || o.name || o.uuid;

function readCount(equilibrationS: number, intervalS: number, totalTimeS: number): number {
  const times: number[] = [0];
  if (30 <= totalTimeS) times.push(30);
  let t = times[times.length - 1];
  while (t + intervalS <= totalTimeS + 1e-9) {
    t += intervalS;
    times.push(t);
  }
  if (Math.abs(times[times.length - 1] - totalTimeS) > 1e-9) times.push(totalTimeS);
  return times.length;
}

export default function PlatereaderKineticTestScreen() {
  const schemaDefault = (name: string, fallback: unknown) =>
    zeon.schema.find((s) => s.name === name)?.defaultValue ?? fallback;
  const initial = (name: string, fallback: unknown) => zeon.defaults[name] ?? schemaDefault(name, fallback);

  const byType = (types: string[]) =>
    zeon.worldObjects.filter((o) => o.meshType !== undefined && types.includes(o.meshType));
  const objectOptions = (types: string[]) => {
    const xs = byType(types);
    return xs.length ? xs : zeon.worldObjects;
  };
  const firstName = (types: string[], fallback: string) =>
    objectOptions(types)[0] ? objName(objectOptions(types)[0]) : fallback;

  const [assayPlate, setAssayPlate] = useState(String(initial("assay_plate", firstName(["wellplate_96_flatbottom"], "wellplate_96_flatbottom"))));
  const [platereader, setPlatereader] = useState(String(initial("platereader", firstName(["plate_reader"], "plate_reader"))));
  const [plateHome, setPlateHome] = useState(String(initial("plate_home", firstName(["wellplate_holder"], "wellplate_holder_tags"))));
  const [intervalS, setIntervalS] = useState(Number(initial("kinetic_interval_s", 30)));
  const [totalTimeS, setTotalTimeS] = useState(Number(initial("kinetic_total_time_s", 180)));
  const [temperatureC, setTemperatureC] = useState(Number(initial("reader_temperature_c", 25)));
  const [equilibrationS, setEquilibrationS] = useState(Number(initial("reader_equilibration_s", 30)));
  const [runName, setRunName] = useState(String(initial("run_name", "platereader_kinetic_test")));

  const reads = useMemo(() => readCount(equilibrationS, intervalS, totalTimeS), [equilibrationS, intervalS, totalTimeS]);
  const totalPlateTimeS = equilibrationS + totalTimeS;

  useEffect(() => {
    zeon.setConfirmed?.(true);
    zeon.setDirty?.(false);
  }, []);

  const submit = () => {
    zeon.submit({
      assay_plate: assayPlate,
      platereader,
      plate_home: plateHome,
      kinetic_second_read_s: 30,
      kinetic_interval_s: intervalS,
      kinetic_total_time_s: totalTimeS,
      reader_temperature_c: temperatureC,
      reader_equilibration_s: equilibrationS,
      slope_window_start_s: 60,
      slope_window_end_s: totalTimeS,
      export_extension: "csv",
      run_name: runName,
    });
  };

  const renderObjectSelect = (label: string, value: string, setValue: (v: string) => void, types: string[]) => (
    <div>
      <label style={STYLE.label}>{label}</label>
      <select style={STYLE.field} value={value} onChange={(e) => setValue(e.target.value)}>
        {objectOptions(types).map((o) => (
          <option key={o.uuid} value={objName(o)}>
            {objName(o)}
          </option>
        ))}
      </select>
    </div>
  );

  return (
    <div style={STYLE.page}>
      <div style={STYLE.content}>
        <div style={STYLE.eyebrow}>Integration test</div>
        <h1 style={STYLE.h1}>Plate reader kinetic test</h1>
        <p style={STYLE.sub}>
          Short run to validate load → close → one Gen5 kinetic export → unload. Default:{" "}
          <strong>25 °C</strong>, reads every <strong>30 s</strong> for <strong>3 min</strong>.
        </p>

        <div style={STYLE.card}>
          <div style={STYLE.grid2}>
            {renderObjectSelect("Assay plate", assayPlate, setAssayPlate, ["wellplate_96_flatbottom"])}
            {renderObjectSelect("Plate reader", platereader, setPlatereader, ["plate_reader"])}
            {renderObjectSelect("Plate home", plateHome, setPlateHome, ["wellplate_holder"])}
            <div>
              <label style={STYLE.label}>Run name</label>
              <input style={STYLE.field} value={runName} onChange={(e) => setRunName(e.target.value)} />
            </div>
          </div>
        </div>

        <div style={STYLE.card}>
          <div style={STYLE.grid2}>
            <div>
              <label style={STYLE.label}>Temperature (°C)</label>
              <input style={STYLE.field} type="number" step="0.1" value={temperatureC} onChange={(e) => setTemperatureC(Number(e.target.value))} />
            </div>
            <div>
              <label style={STYLE.label}>Equilibration (s)</label>
              <input style={STYLE.field} type="number" step="1" value={equilibrationS} onChange={(e) => setEquilibrationS(Number(e.target.value))} />
            </div>
            <div>
              <label style={STYLE.label}>Read interval (s)</label>
              <input style={STYLE.field} type="number" step="1" value={intervalS} onChange={(e) => setIntervalS(Number(e.target.value))} />
            </div>
            <div>
              <label style={STYLE.label}>Kinetic window (s)</label>
              <input style={STYLE.field} type="number" step="1" value={totalTimeS} onChange={(e) => setTotalTimeS(Number(e.target.value))} />
            </div>
          </div>
          <div style={STYLE.statGrid}>
            <div style={STYLE.stat}>
              <div style={STYLE.statLabel}>Read count</div>
              <div style={STYLE.statValue}>{reads}</div>
            </div>
            <div style={STYLE.stat}>
              <div style={STYLE.statLabel}>In reader</div>
              <div style={STYLE.statValue}>{Math.round(totalPlateTimeS / 60 * 10) / 10} min</div>
            </div>
            <div style={STYLE.stat}>
              <div style={STYLE.statLabel}>Gen5 wait</div>
              <div style={STYLE.statValue}>{totalPlateTimeS + 60}s</div>
            </div>
          </div>
          <p style={STYLE.note}>
            Gen5 needs a saved <em>test</em> kinetic protocol matching these settings (or reuse the production protocol with a shorter window for dry runs).
          </p>
        </div>

        <button type="button" style={STYLE.button} onClick={submit}>
          Run plate reader kinetic test
        </button>
      </div>
    </div>
  );
}
