// --- GeCCo Pipeline ---
// Guided generation of Computational Cognitive models (Rmus et al., NeurIPS 2025)
//
// Pipeline: given a task description + behavioral data, use an LLM to generate
// a Python function implementing a cognitive model, then iterate based on
// predictive performance feedback.
//
// Since GeCCo has no public repo, we implement the pipeline from the paper.
// The generated models are Python functions (NOT Stan/PyMC).
// For ThinkHigher, we generate models that predict:
//   - Response strategy given stage context
//   - RT given cognitive load indicators
//   - Learning trajectory across stages

import { callLLM } from "./llm";
import type { TranscriptEntry } from "./types";
import type { CognitiveSignals } from "./rt-metrics";

export interface GeCCoModel {
  id: string;
  name: string;
  description: string;
  // The generated model as a serialized representation
  // In production: Python function string sent to a JAX execution backend
  // In the Next.js layer: we store the model spec and parameters
  modelSpec: string;
  parameters: Record<string, number>;
  fitness: number; // How well it fits held-out data (lower = better, negative log-likelihood)
  generatedAt: number;
}

export interface GeCCoModelCandidate {
  spec: string;
  rationale: string;
}

// Generate candidate cognitive models for a participant's behavioral data.
// Uses the project's LLM (Gemini) as the model generator, following GeCCo's pipeline.
export async function generateModelCandidates(
  taskDescription: string,
  signals: CognitiveSignals,
  priorModels: GeCCoModel[]
): Promise<GeCCoModelCandidate[]> {
  const dataContext = formatSignalsForLLM(signals);
  const priorContext =
    priorModels.length > 0
      ? `Previously generated models and their fitness scores:\n${priorModels
          .map((m) => `- ${m.name} (fitness: ${m.fitness.toFixed(3)}): ${m.description}`)
          .join("\n")}\n\nImprove on these models.`
      : "No prior models exist yet. Generate initial candidates.";

  const prompt = `You are a computational cognitive scientist. Given a behavioral task and participant data, propose a cognitive model that predicts the participant's response patterns.

TASK DESCRIPTION:
${taskDescription}

BEHAVIORAL DATA:
${dataContext}

${priorContext}

Generate exactly 3 candidate cognitive models. For each, provide:
1. A short name
2. A rationale explaining the cognitive mechanism
3. A model specification as a JSON object with:
   - "type": one of "learning-rate", "dual-process", "drift-diffusion", "bayesian-update"
   - "parameters": named parameters with initial values
   - "predicts": what behavioral variable it models (e.g., "rt", "strategy", "engagement")
   - "equations": informal description of the generative process

Return a JSON array of objects: [{"name": "...", "rationale": "...", "spec": {...}}, ...]
Return ONLY the JSON array, no other text.`;

  try {
    const raw = await callLLM({
      system:
        "You are an expert computational cognitive scientist specializing in Bayesian cognitive models and reinforcement learning. Return only valid JSON.",
      messages: [{ role: "user", content: prompt }],
      maxTokens: 2000,
    });

    const clean = raw.replace(/```json|```/g, "").trim();
    const candidates = JSON.parse(clean) as Array<{
      name: string;
      rationale: string;
      spec: Record<string, unknown>;
    }>;

    return candidates.map((c) => ({
      spec: JSON.stringify(c.spec),
      rationale: `${c.name}: ${c.rationale}`,
    }));
  } catch {
    return [];
  }
}

// Format cognitive signals into a human-readable summary for the LLM.
function formatSignalsForLLM(signals: CognitiveSignals): string {
  const lines: string[] = [];

  for (const stage of signals.stages) {
    lines.push(`Stage "${stage.stageId}":`);
    lines.push(`  Turns: ${stage.turnCount}`);
    lines.push(`  Mean RT: ${stage.meanRT.toFixed(0)}ms (SD: ${stage.sdRT.toFixed(0)}ms)`);
    lines.push(`  RT trend (slope): ${stage.rtSlope.toFixed(1)}ms/turn`);
    lines.push(`  Mean deliberation time: ${stage.meanDeliberation.toFixed(0)}ms`);
    lines.push(`  RT coefficient of variation: ${stage.rtCoeffOfVariation.toFixed(3)}`);
  }

  lines.push("");
  lines.push("Cross-stage signals:");
  lines.push(`  Automation bias risk: ${(signals.automationBiasRisk * 100).toFixed(1)}%`);
  lines.push(`  Stage transition RT effect: ${signals.stageTransitionEffect.toFixed(0)}ms`);
  lines.push(`  Session fatigue slope: ${signals.sessionFatigueSlope.toFixed(1)}ms/turn`);
  lines.push(`  Engagement ratio: ${(signals.engagementRatio * 100).toFixed(1)}%`);
  lines.push(`  Total user messages: ${signals.allUserRTs.length}`);

  if (signals.allUserRTs.length > 0) {
    const mean = signals.allUserRTs.reduce((a, b) => a + b, 0) / signals.allUserRTs.length;
    lines.push(`  Overall mean RT: ${mean.toFixed(0)}ms`);
    lines.push(`  RT sequence: [${signals.allUserRTs.map((r) => r.toFixed(0)).join(", ")}]`);
  }
  if (signals.allUserMessageLengths.length > 0) {
    lines.push(
      `  Message length sequence: [${signals.allUserMessageLengths.join(", ")}]`
    );
  }

  return lines.join("\n");
}

// Score a candidate model against held-out behavioral data.
// In production, this would execute the Python model via a JAX backend.
// For now, we use a simple heuristic fit metric.
export function scoreModel(
  candidate: GeCCoModelCandidate,
  signals: CognitiveSignals
): number {
  try {
    const spec = JSON.parse(candidate.spec);

    // Simple fitness heuristic: does the model type match the data patterns?
    let fitness = 0;

    if (spec.type === "learning-rate" && signals.allUserRTs.length >= 3) {
      // Check if RT actually shows a learning curve
      const slope = signals.sessionFatigueSlope;
      fitness = slope < 0 ? -Math.abs(slope) : Math.abs(slope);
    } else if (spec.type === "dual-process") {
      // Dual-process models are good when RT variance is high
      const meanCv =
        signals.stages.reduce((a, s) => a + s.rtCoeffOfVariation, 0) /
        signals.stages.length;
      fitness = -meanCv; // Lower CV = worse fit for dual-process
    } else if (spec.type === "drift-diffusion") {
      // DDM fits well when there's clear speed-accuracy tradeoff signal
      fitness = -Math.abs(signals.sessionFatigueSlope);
    } else {
      fitness = 0;
    }

    return fitness;
  } catch {
    return Infinity; // Unparseable = worst fitness
  }
}

// Full GeCCo iteration: generate candidates, score them, return the best.
export async function runGeCCoPipeline(
  taskDescription: string,
  signals: CognitiveSignals,
  iterations: number = 2
): Promise<GeCCoModel | null> {
  let bestModels: GeCCoModel[] = [];

  for (let i = 0; i < iterations; i++) {
    const candidates = await generateModelCandidates(taskDescription, signals, bestModels);
    if (candidates.length === 0) break;

    for (const candidate of candidates) {
      const fitness = scoreModel(candidate, signals);
      bestModels.push({
        id: `gecco-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`,
        name: candidate.rationale.split(":")[0],
        description: candidate.rationale,
        modelSpec: candidate.spec,
        parameters: {},
        fitness,
        generatedAt: Date.now(),
      });
    }

    // Keep top 3 for next iteration
    bestModels.sort((a, b) => a.fitness - b.fitness);
    bestModels = bestModels.slice(0, 3);
  }

  return bestModels.length > 0 ? bestModels[0] : null;
}
