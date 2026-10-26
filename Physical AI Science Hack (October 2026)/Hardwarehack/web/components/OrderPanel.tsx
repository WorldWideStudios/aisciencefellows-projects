"use client";
// The order: which columns brew, the tips and troughs it uses, what's wrong, and the Brew button.
import type { ConsoleState, PlanResult, Recipe } from "@/lib/apothecary";

interface Props {
  recipes: Recipe[];
  plan: PlanResult | null;
  planning: boolean;
  state: ConsoleState;
  brewing: boolean;
  run: { id: string; status: string; errors: string[] } | null;
  onBrew: () => void;
  onRunAction: (action: "pause" | "play" | "stop") => void;
  onTipsRefilled: () => void;
  onNewPlate: () => void;
}

const ACTIVE = new Set(["idle", "running", "paused", "finishing", "stop-requested", "awaiting-recovery"]);

export default function OrderPanel(p: Props) {
  const { recipes, plan, state } = p;
  const ready = recipes.length > 0 && plan !== null && plan.problems.length === 0 && plan.simulation?.ok === true;
  const tipsLine = (label: string, need: number, left: number) => (
    <div className="flex justify-between text-sm">
      <span>{label}</span>
      <span className={need > left ? "text-alert" : "text-ink-soft"}>{need} needed, {left} left</span>
    </div>
  );
  return (
    <section aria-labelledby="order-title" className="flex flex-col gap-3">
      <div>
        <h2 id="order-title" className="section-title">Order</h2>
        {recipes.length === 0 ? (
          <p className="text-xs text-ink-soft">Pick a column on the plate and give it ingredients.</p>
        ) : (
          <ul className="mt-1 flex max-h-28 flex-col gap-0.5 overflow-y-auto text-sm">
            {recipes.map((r) => (
              <li key={r.column} className="flex justify-between gap-3">
                <span>{r.name}</span>
                <span className="shrink-0 whitespace-nowrap text-ink-soft">{r.ingredients.length} ingredient{r.ingredients.length === 1 ? "" : "s"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {plan && recipes.length > 0 && (
        <div className="flex flex-col gap-1 border-t border-mithril-soft pt-3">
          {tipsLine("50 µL filter tips (A2)", plan.summary.small_tips, state.tips.small_left)}
          {tipsLine("1000 µL tips (A1)", plan.summary.large_tips, state.tips.large_left)}
        </div>
      )}

      {plan && plan.problems.length > 0 && (
        <ul className="max-h-24 overflow-y-auto rounded-md bg-alert-wash px-3 py-2 text-xs text-alert">
          {plan.problems.map((problem) => <li key={problem}>{problem.charAt(0).toUpperCase() + problem.slice(1)}.</li>)}
        </ul>
      )}
      {plan?.simulation && (
        <p className={`text-xs ${plan.simulation.ok ? "text-leaf" : "text-alert"}`}>
          {plan.simulation.ok ? `Simulated on the Opentrons simulator: ${plan.simulation.steps} steps, no errors.` : `Simulation failed: ${plan.simulation.error}`}
        </p>
      )}
      {!state.robot.mock && !state.calibrated && (
        <p className="text-sm text-alert">The plate in B3 isn&apos;t calibrated on this laptop. Run flex calibrate at the robot before brewing.</p>
      )}

      <button className="btn btn-primary py-2.5 text-base" disabled={!ready || p.brewing || p.planning} onClick={p.onBrew}>
        {p.brewing ? "Brewing…" : p.planning ? "Checking the order…"
          : recipes.length ? `Brew ${recipes.length} column${recipes.length === 1 ? "" : "s"}` : "Brew"}
      </button>

      {p.run && (
        <div className="flex items-center justify-between gap-2 rounded-md border border-mithril bg-surface px-3 py-2 text-sm">
          <span>
            Run {p.run.id.slice(0, 8)}: <span className={p.run.status === "succeeded" ? "text-leaf" : ACTIVE.has(p.run.status) ? "text-amber" : "text-alert"}>{p.run.status}</span>
          </span>
          {ACTIVE.has(p.run.status) && (
            <span className="flex gap-1">
              {p.run.status === "paused"
                ? <button className="btn" onClick={() => p.onRunAction("play")}>Resume</button>
                : <button className="btn" onClick={() => p.onRunAction("pause")}>Pause</button>}
              <button className="btn text-alert" onClick={() => p.onRunAction("stop")}>Stop</button>
            </span>
          )}
        </div>
      )}

      <div className="flex flex-wrap gap-x-2 border-t border-mithril-soft pt-2">
        <button className="btn btn-quiet" onClick={p.onTipsRefilled}>Tip racks refilled</button>
        <button className="btn btn-quiet" onClick={p.onNewPlate}>New plate</button>
      </div>
    </section>
  );
}
