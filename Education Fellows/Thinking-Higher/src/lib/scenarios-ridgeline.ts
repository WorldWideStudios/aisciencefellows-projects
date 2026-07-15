import { SimulationV2, StageV2Runtime } from "./types";
import scenarioJson from "@/data/scenarios/003-ridgeline-analyst-sim-001.json";

export const RIDGELINE_SCENARIO: SimulationV2 = scenarioJson as unknown as SimulationV2;

// Resolve each stage's primary agent from the agents dict
export const RIDGELINE_STAGES: StageV2Runtime[] = RIDGELINE_SCENARIO.stages.map((stage) => {
  const primaryAgentId = stage.agentIds[0];
  const agent = RIDGELINE_SCENARIO.agents[primaryAgentId];
  if (!agent) throw new Error(`Agent "${primaryAgentId}" not found for stage "${stage.id}"`);
  return { ...stage, agent };
});
