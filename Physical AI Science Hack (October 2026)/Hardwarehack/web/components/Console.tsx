"use client";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { orderable, withDefaultNames, type ConsoleState, type PlanResult, type Recipe, type Trough } from "@/lib/apothecary";
import { api } from "@/lib/api";
import { DEFAULT_TEMPLATE_ID, draftsSignature, inferTemplate, TEMPLATES, templateDrafts } from "@/lib/templates";
import OrderPanel from "./OrderPanel";
import PlateView from "./PlateView";
import RecipeEditor from "./RecipeEditor";
import RobotControl from "./RobotControl";
import TroughList from "./TroughList";
import WizardMark from "./WizardMark";

type Drafts = Record<number, Recipe>;
const ACTIVE = new Set(["idle", "running", "paused", "finishing", "stop-requested", "awaiting-recovery"]);

// Per-viewer conveniences only; the order itself is checked by the API.
const store = {
  get<T>(key: string, fallback: T): T {
    try { const v = localStorage.getItem(key); return v ? (JSON.parse(v) as T) : fallback; } catch { return fallback; }
  },
  set(key: string, value: unknown) { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* storage unavailable */ } },
  has(key: string): boolean { try { return localStorage.getItem(key) !== null; } catch { return false; } },
};
const draftsKey = (plate: string) => `athelas.drafts.${plate}`;
const templateKey = (plate: string) => `athelas.template.${plate}`;
// Which template the plate's order came from, and the drafts it produced (to tell if they were edited).
type Loaded = { id: string; snapshot: string } | null;
// A plate opened for the first time starts with the default template (the single-agent panel).
const initialDrafts = (plate: string): Record<number, Recipe> =>
  store.has(draftsKey(plate)) ? store.get(draftsKey(plate), {}) : templateDrafts(DEFAULT_TEMPLATE_ID);
const initialLoaded = (plate: string): Loaded => {
  if (!store.has(draftsKey(plate))) {
    return { id: DEFAULT_TEMPLATE_ID, snapshot: draftsSignature(templateDrafts(DEFAULT_TEMPLATE_ID)) };
  }
  const saved = store.get<Loaded>(templateKey(plate), null);
  // Snapshots are signatures ("[...]"); a missing or older record is recognised from the recipes.
  if (saved && saved.snapshot.startsWith("[")) return saved;
  return store.has(templateKey(plate)) && saved === null ? null : inferTemplate(store.get(draftsKey(plate), {}));
};

export default function Console() {
  // Rendered only in the browser (see ClientConsole), so saved drafts can be read up front.
  const [plate, setPlate] = useState(() => store.get("athelas.plate", "Batch 1"));
  const [state, setState] = useState<ConsoleState | null>(null);
  const [drafts, setDrafts] = useState<Drafts>(() => initialDrafts(store.get("athelas.plate", "Batch 1")));
  const [loaded, setLoaded] = useState<Loaded>(() => initialLoaded(store.get("athelas.plate", "Batch 1")));
  const [selected, setSelected] = useState(1);
  const [plan, setPlan] = useState<(PlanResult & { key: string }) | null>(null);
  const [brewing, setBrewing] = useState(false);
  const [justBrewed, setJustBrewed] = useState<number[]>([]);
  const [run, setRun] = useState<{ id: string; status: string; errors: string[] } | null>(null);
  const [message, setMessage] = useState<{ text: string; bad: boolean } | null>(null);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);
  const troughSave = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    try {
      setState(await api.state(plate));
    } catch (e) {
      setMessage({ text: (e as Error).message, bad: true });
    }
  }, [plate]);
  useEffect(() => {
    api.state(plate).then((s) => { setState(s); setMessage(null); })
      .catch((e: Error) => setMessage({ text: e.message, bad: true }));
  }, [plate]);

  // Unnamed columns carry a default name that follows the plate name ("Batch 2 column 3").
  const recipes = useMemo(
    () => withDefaultNames(plate, orderable(drafts).filter((r) => !state?.columns[String(r.column)])),
    [drafts, state, plate]);

  // Check the order with the API (rules + simulator) shortly after each edit. Each result carries the
  // order it was checked for, so a check of an older version of the order never enables Brew.
  const orderKey = useMemo(() => JSON.stringify({ plate, recipes, tips: state?.tips, troughs: state?.troughs }), [plate, recipes, state]);
  useEffect(() => {
    if (recipes.length === 0) return;
    const timer = setTimeout(() => {
      api.plan(plate, recipes).then((result) => setPlan({ ...result, key: orderKey }))
        .catch((e: Error) => setMessage({ text: e.message, bad: true }));
    }, 500);
    return () => clearTimeout(timer);
  }, [orderKey, plate, recipes]);
  const currentPlan = recipes.length > 0 && plan?.key === orderKey ? plan : null;
  const planning = recipes.length > 0 && currentPlan === null;

  const editDrafts = (next: Drafts) => {
    setDrafts(next);
    // A fresh plate's default template lives only in memory until its drafts are first saved.
    if (!store.has(draftsKey(plate))) store.set(templateKey(plate), loaded);
    store.set(draftsKey(plate), next);
  };
  const rememberTemplate = (next: Loaded) => { setLoaded(next); store.set(templateKey(plate), next); };
  const edited = loaded !== null && draftsSignature(drafts) !== loaded.snapshot;
  const hasDraftWork = Object.values(drafts).some((r) => r.ingredients.length > 0 && !state?.columns[String(r.column)]);
  const loadTemplate = (id: string) => {
    const template = TEMPLATES.find((t) => t.id === id);
    if (!template) return;
    if (hasDraftWork && !window.confirm(`Replace the recipes you've entered with "${template.name}"?`)) return;
    const free = Array.from({ length: 12 }, (_, i) => i + 1).filter((c) => !state?.columns[String(c)]);
    if (free.length === 0) { setMessage({ text: "Every column of this plate is brewed. Start a new plate first.", bad: true }); return; }
    const next = templateDrafts(id, free);
    editDrafts(next);
    rememberTemplate({ id, snapshot: draftsSignature(next) });
    setSelected(free[0]);
  };
  const clearOrder = () => {
    if (hasDraftWork && !window.confirm("Clear every recipe in this order?")) return;
    editDrafts({});
    rememberTemplate(null);
  };
  const recipeFor = (column: number): Recipe => drafts[column] ?? { column, name: "", ingredients: [] };

  const editTrough = (trough: Trough) => {
    if (!state) return;
    const troughs = state.troughs.map((t) => (t.trough === trough.trough ? trough : t));
    setState({ ...state, troughs });
    if (troughSave.current) clearTimeout(troughSave.current);
    troughSave.current = setTimeout(() => {
      api.saveTroughs(troughs).catch((e: Error) => setMessage({ text: e.message, bad: true }));
    }, 500);
  };

  const stopPolling = () => { if (poll.current) clearInterval(poll.current); poll.current = null; };
  useEffect(() => stopPolling, []);
  const follow = (id: string) => {
    stopPolling();
    poll.current = setInterval(async () => {
      try {
        const status = await api.runStatus(id);
        setRun(status);
        if (!ACTIVE.has(status.status)) stopPolling();
      } catch (e) { setMessage({ text: (e as Error).message, bad: true }); stopPolling(); }
    }, 2000);
  };

  const brew = async () => {
    if (!state) return;
    const where = state.robot.mock ? "the mock robot" : `the robot at ${state.robot.host}`;
    const columns = recipes.map((r) => r.column);
    if (!window.confirm(`Brew column${columns.length === 1 ? "" : "s"} ${columns.join(", ")} on ${where}?\n\nCheck the reservoir, tip racks and plate are loaded.`)) return;
    setBrewing(true);
    try {
      const result = await api.brew(plate, recipes);
      const next = { ...drafts };
      columns.forEach((c) => delete next[c]);
      editDrafts(next);
      // Brewed columns leave the draft; that isn't an edit of the template.
      if (loaded) rememberTemplate({ ...loaded, snapshot: draftsSignature(next) });
      setJustBrewed(columns);
      setTimeout(() => setJustBrewed([]), 900 + columns.length * 140);
      setRun({ id: result.run_id, status: "running", errors: [] });
      follow(result.run_id);
      setMessage({ text: `Brewing ${columns.length} column${columns.length === 1 ? "" : "s"}: ${result.steps} steps.`, bad: false });
      await load();
    } catch (e) {
      setMessage({ text: (e as Error).message, bad: true });
    } finally {
      setBrewing(false);
    }
  };

  const changePlate = (name: string) => {
    setPlate(name);
    store.set("athelas.plate", name);
    setDrafts(initialDrafts(name));
    setLoaded(initialLoaded(name));
  };

  return (
    // Desktop: exactly one screen, no page scroll; panels scroll inside if a screen is short.
    // Below lg the panels stack and the page scrolls normally.
    <div className="mx-auto flex min-h-screen max-w-[1920px] flex-col px-4 lg:h-screen lg:overflow-hidden lg:px-6">
      <header className="header-rule flex shrink-0 flex-wrap items-center gap-3 border-b border-mithril py-2.5">
        <div className="brand-mark relative">
          <WizardMark size={28} />
          {/* a few sparkles around the wizard, twinkling at staggered times */}
          {[
            { left: -6, top: 2, delay: "0s" }, { left: 26, top: -4, delay: "1.3s" },
            { left: 30, top: 18, delay: "2.4s" }, { left: -4, top: 22, delay: "3.1s" },
          ].map((s, i) => (
            <span key={i} className="sparkle" style={{ left: s.left, top: s.top, animationDelay: s.delay }} aria-hidden="true" />
          ))}
        </div>
        <div className="mr-auto">
          <div className="wordmark font-[family-name:var(--font-display)] text-xl leading-none">Athelas Apothecary</div>
          <div className="text-xs text-ink-soft">Concoctions on demand, mixed by an Opentrons Flex</div>
        </div>
        <label className="flex items-center gap-2 text-sm text-ink-soft">
          Template
          {/* Shows the template this plate's order came from; "(edited)" once the recipes change. */}
          <select className="field w-60" value={loaded?.id ?? ""} aria-label="Template"
                  onChange={(e) => loadTemplate(e.target.value)}>
            <option value="" disabled>Load a template…</option>
            {TEMPLATES.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name}{loaded?.id === t.id && edited ? " (edited)" : ` (${t.recipes.length} columns)`}
              </option>
            ))}
          </select>
        </label>
        <button className="btn" onClick={clearOrder} disabled={!hasDraftWork}>Clear order</button>
        <label className="flex items-center gap-2 text-sm text-ink-soft">
          Plate
          <input className="field w-36" value={plate} maxLength={80} aria-label="Plate name"
                 onChange={(e) => changePlate(e.target.value || "Batch 1")} />
        </label>
        <RobotControl onChange={load} />
      </header>

      {message && (
        <p role="status" className={`fixed bottom-4 left-1/2 z-20 max-w-[90vw] -translate-x-1/2 rounded-md border px-4 py-2 text-sm shadow-lg ${
          message.bad ? "border-alert bg-alert-wash text-alert" : "border-leaf bg-leaf-wash text-leaf"}`}>
          {message.text}
          <button className="ml-3 text-ink-soft hover:text-ink" onClick={() => setMessage(null)} aria-label="Dismiss">Close</button>
        </p>
      )}

      {!state ? (
        <p className="py-16 text-ink-soft">Loading the console…</p>
      ) : (
        <main className="grid flex-1 gap-5 py-4 lg:min-h-0 lg:grid-cols-[19.5rem_minmax(0,1fr)_21rem]">
          <TroughList troughs={state.troughs} draws={currentPlan?.summary.trough_draw_ul ?? {}} selectedColumn={selected}
                      canAdd={!state.columns[String(selected)]}
                      onChange={editTrough}
                      onAdd={(trough) => {
                        const recipe = recipeFor(selected);
                        editDrafts({ ...drafts, [selected]: { ...recipe, ingredients: [...recipe.ingredients, { trough, volume_ul: 10 }] } });
                      }} />
          <section aria-labelledby="plate-title" className="flex min-h-0 flex-col">
            <div className="mb-1 flex shrink-0 items-baseline justify-between gap-4">
              <h1 id="plate-title" className="font-[family-name:var(--font-display)] text-2xl leading-tight">{plate}</h1>
              <span className="text-xs text-ink-soft">Armadillo 96-well PCR plate, slot B3</span>
            </div>
            <div className="min-h-0 flex-1">
              <PlateView troughs={state.troughs} drafts={drafts} brewed={state.columns} selected={selected}
                         justBrewed={justBrewed} onSelect={setSelected} />
            </div>
          </section>
          {/* Right panel runs to the bottom of the screen: recipe on top (scrolls if long),
              the order and Brew button pinned to the bottom. */}
          <div className="flex min-h-0 flex-col rounded-lg border border-mithril bg-surface lg:h-full">
            <div className="min-h-0 flex-1 overflow-y-auto p-3">
              <RecipeEditor column={selected} plate={plate} recipe={recipeFor(selected)} brewed={state.columns[String(selected)]}
                            troughs={state.troughs} onChange={(recipe) => editDrafts({ ...drafts, [selected]: recipe })} />
            </div>
            <div className="shrink-0 border-t border-mithril p-3">
              <OrderPanel recipes={recipes} plan={currentPlan} planning={planning} state={state} brewing={brewing} run={run}
                          onBrew={brew}
                          onRunAction={async (action) => {
                            if (!run) return;
                            try { await api.runAction(run.id, action); follow(run.id); } catch (e) { setMessage({ text: (e as Error).message, bad: true }); }
                          }}
                          onTipsRefilled={async () => {
                            if (!window.confirm("Mark both tip racks (A1 and A2) as full again?")) return;
                            await api.tipsRefilled(); await load();
                          }}
                          onNewPlate={async () => {
                            if (!window.confirm(`Start a fresh plate as "${plate}"? Its brewed columns are forgotten.`)) return;
                            await api.clearPlate(plate); await load();
                          }} />
            </div>
          </div>
        </main>
      )}
    </div>
  );
}
