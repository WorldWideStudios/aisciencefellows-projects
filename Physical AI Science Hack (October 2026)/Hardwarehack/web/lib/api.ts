// Typed calls to the local Python API (proxied at /api by next.config.ts).
import type { ConsoleState, PlanResult, Recipe, Trough } from "./apothecary";

export interface RobotConfig { host: string; port: number; mock: boolean }
export interface RunStatus { id: string; status: string; errors: string[] }

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, {
      ...init,
      headers: init?.body ? { "Content-Type": "application/json", ...init.headers } : init?.headers,
    });
  } catch {
    throw new Error("Can't reach the local API on 127.0.0.1:8000. Start it with: uv run python scripts/serve.py");
  }
  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string"
        ? body.detail
        : Array.isArray(body.detail)
          ? body.detail.map((d: { loc?: string[]; msg?: string }) => `${d.loc?.at(-1) ?? "input"}: ${d.msg}`).join("; ")
          : JSON.stringify(body.detail ?? body);
    } catch {
      if (response.status >= 500) detail = "The local API isn't running (start scripts/serve.py)";
    }
    throw new Error(detail);
  }
  return response.json();
}

const json = (body: unknown) => JSON.stringify(body);
const enc = encodeURIComponent;

export const api = {
  state: (plate: string) => call<ConsoleState>(`/apothecary/state?plate=${enc(plate)}`),
  saveTroughs: (troughs: Trough[]) => call<Trough[]>("/apothecary/troughs", { method: "PUT", body: json(troughs) }),
  plan: (plate: string, recipes: Recipe[]) =>
    call<PlanResult>("/apothecary/plan", { method: "POST", body: json({ plate, recipes }) }),
  brew: (plate: string, recipes: Recipe[]) =>
    call<{ run_id: string; steps: number }>("/apothecary/brew", { method: "POST", body: json({ plate, recipes }) }),
  tipsRefilled: () => call<unknown>("/apothecary/tips-refilled", { method: "POST" }),
  clearPlate: (plate: string) => call<unknown>(`/apothecary/plates/${enc(plate)}/clear`, { method: "POST" }),
  robotConfig: () => call<RobotConfig>("/robot/config"),
  setRobotConfig: (config: RobotConfig) => call<RobotConfig>("/robot/config", { method: "PUT", body: json(config) }),
  health: () => call<{ name?: string; robot_model?: string; api_version?: string }>("/robot/health"),
  runStatus: (runId: string) => call<RunStatus>(`/robot/runs/${runId}`),
  runAction: (runId: string, action: "play" | "pause" | "stop") =>
    call<unknown>(`/robot/runs/${runId}/${action}`, { method: "POST" }),
};
