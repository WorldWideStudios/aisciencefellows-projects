// Bench twin simulation core (pure functions; no DOM). Every number marked ASSUMED is a planning
// placeholder, not a measurement.
const ANALOGS = [ // nominal size from the BioKEA Track A kit; other dims + densities ASSUMED
  {cls: "chia seed", dims: [2.0, 1.4, 1.0], rho: 1.10, fragile: false},
  {cls: "couscous", dims: [2.0, 1.8, 1.6], rho: 1.40, fragile: false},
  {cls: "white rice", dims: [6.0, 2.0, 1.6], rho: 1.45, fragile: false},
  {cls: "ditalini", dims: [7.0, 6.0, 6.0], rho: 1.30, fragile: false},
  {cls: "wild rice", dims: [10.0, 1.6, 1.4], rho: 1.35, fragile: false},
  {cls: "fideo", dims: [15.0, 1.2, 1.2], rho: 1.40, fragile: true},
  {cls: "egg noodle", dims: [20.0, 6.0, 1.0], rho: 1.40, fragile: true},
  {cls: "campanelle", dims: [25.0, 14.0, 12.0], rho: 1.30, fragile: true},
  {cls: "farfalle", dims: [35.0, 22.0, 8.0], rho: 1.30, fragile: true},
];
const NOVEL_TYPES = [ // synthetic stand-ins for insects the vision model has never seen (ASSUMED shapes)
  {cls: "novel: winged fly-like", dims: [6.0, 4.5, 1.8], rho: 1.04, fragile: true},
  {cls: "novel: long-legged", dims: [12.0, 3.0, 2.0], rho: 1.06, fragile: true},
  {cls: "novel: compact beetle-like", dims: [4.0, 2.6, 2.0], rho: 1.12, fragile: false},
];
const DEBRIS = {cls: "soil grit", dims: [2.0, 1.5, 1.2], rho: 2.65, fragile: false, debris: true};

function mulberry(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed);
  t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function strHash(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
const sorted3 = d => [...d].sort((a, b) => b - a);

function makeSample(cfg) {
  const rnd = mulberry(cfg.seed), items = [];
  const jitter = (d, k) => d.map(x => +(x * (1 + (rnd() - 0.5) * 2 * k)).toFixed(2));
  ANALOGS.forEach(a => { if (!cfg.analogs[a.cls]) return;
    for (let i = 0; i < cfg.perClass; i++) items.push({id: `${a.cls}#${i}`, cls: a.cls, dims: jitter(a.dims, 0.12),
      rho: cfg.wet ? +(1 + (a.rho - 1) * 0.55).toFixed(3) : a.rho, fragile: a.fragile, novel: false, debris: false}); });
  for (let i = 0; i < cfg.novelN; i++) { const t = NOVEL_TYPES[i % NOVEL_TYPES.length];
    items.push({id: `${t.cls}#${i}`, cls: t.cls, dims: jitter(t.dims, 0.15), rho: t.rho, fragile: t.fragile, novel: true, debris: false}); }
  for (let i = 0; i < cfg.debrisN; i++) items.push({id: `grit#${i}`, cls: DEBRIS.cls, dims: jitter(DEBRIS.dims, 0.5), rho: 2.65,
    fragile: false, novel: false, debris: true});
  return items;
}

// passage through an opening (rigid, orientation-free): round/hex/square hole sorts by 2nd dimension,
// slot sorts by the smallest (thickness)
function passes(dims, w, shape, fit = 0.95) { const [a, b, c] = sorted3(dims);
  return shape === "slot" ? c <= w * fit : (b <= w * fit && c <= w * fit); }

function settling(item, rhoF) { // Newton-regime estimate, m/s (ASSUMED Cd 1.0, equivalent sphere)
  const d = Math.cbrt(item.dims.reduce((p, x) => p * x, 1)) / 1000, dr = item.rho - rhoF;
  return Math.sign(dr) * Math.sqrt((4 / 3) * 9.81 * d * Math.abs(dr) / rhoF / 1.0); }

function run(cfg, leaveOut = null) {
  const on = m => cfg.modules[m] && m !== leaveOut;
  const items = makeSample(cfg), stages = [], breaks = [], bins = {};
  const put = (bin, it) => (bins[bin] = bins[bin] || []).push(it);
  let flow = items.slice();
  const rnd = mulberry(cfg.seed + 7);

  // 1 deflocculate: wet samples clump; without surfactant small items ride on large ones (ASSUMED 35%)
  const clumped = new Set();
  if (cfg.wet && !on("deflocculate")) flow.forEach(it => { if (!it.debris && Math.max(...it.dims) < 3 && rnd() < 0.35) clumped.add(it.id); });
  stages.push({stage: "deflocculate", enabled: on("deflocculate"), clumped: clumped.size});

  // 2 density bath: sinkers (rho > liquid) leave as sediment
  if (on("density")) { const keep = [];
    flow.forEach(it => (it.rho > cfg.liquidRho ? put("sediment (density bath)", it) : keep.push(it)));
    stages.push({stage: "density", enabled: true, liquid_g_mL: cfg.liquidRho, sank: flow.length - keep.length}); flow = keep;
  } else stages.push({stage: "density", enabled: false});

  // 3 elutriation: up-flow carries anything that settles slower than the flow; the rest underflows
  if (on("elutriation")) { const keep = [];
    flow.forEach(it => (settling(it, 1.0) > cfg.upflow ? put("underflow (elutriation)", it) : keep.push(it)));
    stages.push({stage: "elutriation", enabled: true, upflow_m_s: cfg.upflow, underflow: flow.length - keep.length}); flow = keep;
  } else stages.push({stage: "elutriation", enabled: false});

  // 4 size sorter
  const sizer = cfg.sizer, damage = [];
  if (on("sizer")) {
    let widths, shape;
    if (sizer === "trommel") { widths = cfg.trommelZones.slice().sort((a, b) => a - b); shape = cfg.trommelShape; }
    else if (sizer === "variable") { widths = cfg.vaWidths.slice().sort((a, b) => a - b); shape = cfg.vaMode === "slot" ? "slot" : "square"; }
    else { widths = cfg.trayStack.slice().sort((a, b) => a - b); shape = "round"; }
    if (sizer === "variable" && !cfg.vaFlush) breaks.push({stage: "sizer", gate: "G_empty", reason: "plates moved with specimens on them: sliding edges shear legs and wings"});
    if (sizer === "variable" && Math.abs(cfg.vaMeasureErr) > 0.1) breaks.push({stage: "sizer", gate: "G_measured", reason: `camera-measured opening off by ${cfg.vaMeasureErr} mm (tolerance 0.10)`});
    const cap = cfg.screenCapacity, crossflow = on("crossflow");
    let remaining = flow.slice();
    widths.forEach((w, k) => {
      const pass = [], stay = [];
      remaining.forEach(it => ((passes(it.dims, w, shape) && !clumped.has(it.id)) ? pass : stay).push(it));
      // blinding: an overloaded screen without cross-flow holds back part of what should pass (ASSUMED model)
      let blinded = 0;
      if (!crossflow && remaining.length > cap) { const f = Math.min(0.6, (remaining.length - cap) / remaining.length);
        for (let i = pass.length - 1; i >= 0; i--) if (rnd() < f) { stay.push(pass.splice(i, 1)[0]); blinded++; } }
      const label = k === 0 ? `< ${w} mm` : `${widths[k - 1]}–${w} mm`;
      pass.forEach(it => put(`size ${label}`, it));
      stages.push({stage: `sizer ${sizer} @${w} mm`, enabled: true, shape, passed: pass.length, blinded});
      remaining = stay;
    });
    remaining.forEach(it => put(`size ≥ ${widths[widths.length - 1]} mm`, it));
    if (sizer === "trommel") { const nc = 42.3 / Math.sqrt(cfg.drumD / 1000), pct = cfg.rpm / nc;
      stages.push({stage: "trommel speed", rpm: cfg.rpm, critical_rpm: +nc.toFixed(1), pct_critical: +(pct * 100).toFixed(0)});
      if (pct > 0.6) flow.forEach(it => it.fragile && damage.push(it.id)); }
    if (cfg.agitation === "vortex" && cfg.vortexRpm > 1500) flow.forEach(it => it.fragile && damage.push(it.id));
    if (cfg.agitation === "centrifuge" && cfg.centrifugeG > 50) flow.forEach(it => it.fragile && damage.push(it.id));
  } else { flow.forEach(it => put("unsorted (no size sorter)", it)); stages.push({stage: "sizer", enabled: false}); }

  // 4b eDNA capture: the wash water that passed every screen goes through a membrane filter; it holds
  // DNA shed by everything in the sample, including what the screens let through (ASSUMED: presence only)
  if (on("edna")) { const fine = Object.entries(bins).filter(([b]) => b.startsWith("size <")).flatMap(([, v]) => v);
    const shed = new Set(items.filter(i => !i.debris).map(i => i.cls));
    stages.push({stage: "eDNA filter", enabled: true, through_every_screen: fine.length, classes_in_wash_water: shed.size});
  } else stages.push({stage: "eDNA filter", enabled: false});

  // 5 vision gate: known classes classified at the model's accuracy; unseen classes are flagged NOVEL
  const known = new Set([...ANALOGS.map(a => a.cls), "soil grit", ...cfg.confirmed]);
  const queue = [], vision = {enabled: on("vision"), correct: 0, wrong: 0, novelFlagged: 0, novelMissed: 0};
  Object.values(bins).flat().forEach(it => {
    if (!on("vision")) return;
    const r = (strHash(it.id + cfg.modelVersion) % 10000) / 10000;
    if (!known.has(it.cls)) { if (r < cfg.novelRecall) { vision.novelFlagged++; queue.push(it); } else vision.novelMissed++; }
    else (r < cfg.accuracy ? vision.correct++ : vision.wrong++);
  });
  stages.push({stage: "vision", ...vision, model: cfg.modelVersion});

  // 6 downstream assay + integrity rules (general practice, flagged as checks, not results)
  const a = cfg.assay, flags = [];
  if (cfg.keepIntact && a === "dna_destructive") breaks.push({stage: "assay", gate: "G_voucher", reason: "destructive grinding conflicts with keeping exoskeleton, wings and legs intact"});
  if (a === "rna" && cfg.preservation === "ethanol") flags.push("RNA from ethanol-stored, dead specimens is usually degraded: use RNAlater or frozen material");
  if (cfg.reagent === "alkaline_lysis") flags.push("Alkaline lysis (Birnboim & Doly 1979) is a plasmid prep: it removes chromosomal DNA, so it is the wrong chemistry for whole-insect genomic DNA");
  if (cfg.keepIntact && cfg.heatC > 60) flags.push(`${cfg.heatC} °C soak: check cuticle and limb integrity (non-destructive protocols commonly soak near 56 °C)`);
  if (damage.length && cfg.keepIntact) flags.push(`${new Set(damage).size} fragile specimens exceed the gentle-handling limits (ASSUMED limits)`);
  stages.push({stage: "assay", assay: a, reagent: cfg.reagent, heat_C: cfg.heatC, preservation: cfg.preservation, flags});

  // 7 arm: every transfer between stations must be within reach (placeholder geometry)
  const arm = ARMS[cfg.arm], transfers = Object.keys(bins).length + 2;
  if (arm.deckOnly && on("sizer") && sizer !== "trays") breaks.push({stage: "arm", gate: "G_footprint", reason: `${arm.name} only moves deck-footprint labware (127.76 × 85.48 mm): use the deck mini-trommel / sieve adapter, not the bench ${sizer}`});
  if (arm.reach_mm < cfg.stationSpacing) breaks.push({stage: "arm", gate: "G_reach", reason: `${arm.name}: station spacing ${cfg.stationSpacing} mm > reach ${arm.reach_mm} mm (placeholder)`});
  if (sizer === "trommel" && on("sizer") && cfg.armTurnsCrank && !arm.parallelJaw) breaks.push({stage: "arm", gate: "G_crank", reason: `${arm.name} has no parallel jaw for the crank knob flats`});
  stages.push({stage: "arm", arm: arm.name, transfers, manual: arm.manual});

  return {items, bins, stages, breaks, flags, queue, metrics: metrics(items, bins, clumped, damage)};
}

const ARMS = { // reach/payload are PLACEHOLDERS until measured
  b601: {name: "Seeed B601-DM", reach_mm: 380, parallelJaw: true, manual: false},
  so101: {name: "SO-101", reach_mm: 280, parallelJaw: true, manual: false},
  gantry: {name: "BugPicker gantry (suction)", reach_mm: 300, parallelJaw: false, manual: false},
  hand: {name: "Human (hand transfer)", reach_mm: 9999, parallelJaw: true, manual: true},
  flex: {name: "Opentrons Flex gripper", reach_mm: 9999, deckOnly: true, parallelJaw: false, manual: false},
};

function metrics(items, bins, clumped, damage) {
  const specimens = items.filter(i => !i.debris), total = specimens.length;
  const binNames = Object.keys(bins), sizeBins = binNames.filter(b => b.startsWith("size") || b.startsWith("unsorted"));
  const inSize = sizeBins.flatMap(b => bins[b]);
  const recovered = inSize.filter(i => !i.debris).length, gritInSpecimens = inSize.filter(i => i.debris).length;
  // purity: share of each size bin made of its most common class
  let pureN = 0; sizeBins.forEach(b => { const c = {}; bins[b].forEach(i => c[i.cls] = (c[i.cls] || 0) + 1); pureN += Math.max(0, ...Object.values(c)); });
  const novel = items.filter(i => i.novel), novelRecovered = inSize.filter(i => i.novel).length;
  return {specimens: total, recovered, recovery: total ? recovered / total : 0, grit_in_specimen_bins: gritInSpecimens,
    purity: inSize.length ? pureN / inSize.length : 0, groups: sizeBins.length, novel_total: novel.length,
    novel_recovered: novelRecovered, clumped: clumped.size, damaged: new Set(damage).size};
}

async function sha256(s) { const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map(x => x.toString(16).padStart(2, "0")).join(""); }
async function merkle(leaves) { let lv = leaves.slice(); if (!lv.length) return null;
  while (lv.length > 1) { if (lv.length % 2) lv.push(lv[lv.length - 1]); const nx = [];
    for (let i = 0; i < lv.length; i += 2) nx.push(await sha256(lv[i] + lv[i + 1])); lv = nx; } return lv[0]; }
function stable(o) { if (Array.isArray(o)) return "[" + o.map(stable).join(",") + "]";
  if (o && typeof o === "object") return "{" + Object.keys(o).sort().map(k => JSON.stringify(k) + ":" + stable(o[k])).join(",") + "}";
  return JSON.stringify(o); }

if (typeof module !== "undefined") module.exports = {run, passes, settling, makeSample, ANALOGS, ARMS, stable};
