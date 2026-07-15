import { Stage, ScenarioDefinition } from "./types";
import scenarioJson from "@/data/scenarios/002-vela-sde-sim-001.json";

// Load the full scenario definition (typed)
export const SCENARIO: ScenarioDefinition = scenarioJson as ScenarioDefinition;

// Export legacy-compatible STAGES array for Simulation.tsx
export const STAGES: Stage[] = SCENARIO.stages.map((s) => ({
  id: s.id,
  name: s.agentProfile.name,
  role: s.agentProfile.role,
  color: s.agentProfile.color,
  badge: s.badge,
  stageTitle: s.stageTitle ?? s.badge,
  desc: s.description,
  avatar: s.agentProfile.avatar,
  systemPrompt: s.agentProfile.personaPrompt,
  stageType: s.stageType ?? "chat",
  videoComponent: s.videoComponent,
  artifactSrc: s.artifactSrc,
  comprehensionQuestions: s.comprehensionQuestions,
  situationBrief: s.situationBrief,
}));

export const SYSTEM_BASE = SCENARIO.systemBase;
