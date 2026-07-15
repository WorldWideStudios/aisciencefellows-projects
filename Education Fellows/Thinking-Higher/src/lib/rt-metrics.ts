import type { TranscriptEntry } from "./types";

// --- Derived RT Metrics ---
// Computed from raw TranscriptEntry[] data collected during simulation.
// These metrics form the basis of the cognitive profile.
// Math follows NivStan patterns (hierarchical Bayesian RL) but computed
// deterministically here; full Bayesian fitting happens in JAX offline.

export interface RTMetrics {
  // Per-stage summary
  stageId: string;
  turnCount: number;
  meanRT: number;
  medianRT: number;
  sdRT: number;
  minRT: number;
  maxRT: number;

  // Trend: slope of RT across turns (negative = speeding up, positive = slowing)
  rtSlope: number;

  // Post-AI-message deliberation: time from AI reply arriving to user starting response
  deliberationTimes: number[];
  meanDeliberation: number;

  // Cognitive load indicators
  rtCoeffOfVariation: number; // sd/mean — high = inconsistent processing
}

export interface CognitiveSignals {
  // Cross-stage patterns
  stages: RTMetrics[];

  // Automation bias indicator: RT decreasing across stages while message
  // length stays constant or decreases (reflexive responding)
  automationBiasRisk: number; // 0-1

  // Adaptability: how much RT changes when transitioning between stages
  // (high = recalibrating cognitive approach per context)
  stageTransitionEffect: number;

  // Fatigue: RT drift (slope) across the entire session
  sessionFatigueSlope: number;

  // Engagement: ratio of substantive turns (>50 chars) to short turns
  engagementRatio: number;

  // Raw data for JAX/Centaur modeling
  allUserRTs: number[];
  allUserMessageLengths: number[];
  allDeliberationTimes: number[];
}

function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

function stddev(values: number[], mean: number): number {
  if (values.length < 2) return 0;
  const sumSq = values.reduce((acc, v) => acc + (v - mean) ** 2, 0);
  return Math.sqrt(sumSq / (values.length - 1));
}

function linearSlope(values: number[]): number {
  if (values.length < 2) return 0;
  const n = values.length;
  const meanX = (n - 1) / 2;
  const meanY = values.reduce((a, b) => a + b, 0) / n;
  let num = 0;
  let den = 0;
  for (let i = 0; i < n; i++) {
    num += (i - meanX) * (values[i] - meanY);
    den += (i - meanX) ** 2;
  }
  return den === 0 ? 0 : num / den;
}

export function computeStageMetrics(stageId: string, entries: TranscriptEntry[]): RTMetrics {
  // Extract user messages with RT
  const userEntries = entries.filter((e) => e.role === "user" && e.responseTimeMs != null);
  const rts = userEntries.map((e) => e.responseTimeMs!);

  // Compute deliberation times: gap between AI message timestamp and next user message timestamp
  const deliberationTimes: number[] = [];
  for (let i = 1; i < entries.length; i++) {
    if (entries[i].role === "user" && entries[i - 1].role === "assistant") {
      deliberationTimes.push(entries[i].timestamp - entries[i - 1].timestamp);
    }
  }

  const mean = rts.length > 0 ? rts.reduce((a, b) => a + b, 0) / rts.length : 0;
  const sd = stddev(rts, mean);

  return {
    stageId,
    turnCount: rts.length,
    meanRT: mean,
    medianRT: median(rts),
    sdRT: sd,
    minRT: rts.length > 0 ? Math.min(...rts) : 0,
    maxRT: rts.length > 0 ? Math.max(...rts) : 0,
    rtSlope: linearSlope(rts),
    deliberationTimes,
    meanDeliberation:
      deliberationTimes.length > 0
        ? deliberationTimes.reduce((a, b) => a + b, 0) / deliberationTimes.length
        : 0,
    rtCoeffOfVariation: mean > 0 ? sd / mean : 0,
  };
}

export function computeCognitiveSignals(
  stageMetrics: RTMetrics[],
  allEntries: Record<string, TranscriptEntry[]>
): CognitiveSignals {
  // Flatten all user RTs and message lengths across stages
  const allUserRTs: number[] = [];
  const allUserMessageLengths: number[] = [];
  const allDeliberationTimes: number[] = [];

  for (const entries of Object.values(allEntries)) {
    for (const e of entries) {
      if (e.role === "user") {
        if (e.responseTimeMs != null) allUserRTs.push(e.responseTimeMs);
        allUserMessageLengths.push(e.content.length);
      }
    }
  }
  for (const m of stageMetrics) {
    allDeliberationTimes.push(...m.deliberationTimes);
  }

  // Automation bias: RT decreasing AND message length decreasing/flat
  const rtSlopes = stageMetrics.map((m) => m.rtSlope);
  const avgRtSlope = rtSlopes.length > 0 ? rtSlopes.reduce((a, b) => a + b, 0) / rtSlopes.length : 0;
  const crossStageRtSlope = linearSlope(stageMetrics.map((m) => m.meanRT));

  // Message lengths per stage
  const stageMsgLens = Object.values(allEntries).map((entries) => {
    const userMsgs = entries.filter((e) => e.role === "user");
    return userMsgs.length > 0
      ? userMsgs.reduce((a, e) => a + e.content.length, 0) / userMsgs.length
      : 0;
  });
  const msgLenSlope = linearSlope(stageMsgLens);

  // Automation bias risk: high when RT decreases AND message length doesn't increase
  let automationBiasRisk = 0;
  if (crossStageRtSlope < 0 && msgLenSlope <= 0) {
    // Normalize: stronger negative RT slope + flat/negative msg length = higher risk
    automationBiasRisk = Math.min(1, Math.abs(crossStageRtSlope) / 5000);
  }

  // Stage transition effect: average absolute change in mean RT between consecutive stages
  let stageTransitionEffect = 0;
  if (stageMetrics.length > 1) {
    let totalChange = 0;
    for (let i = 1; i < stageMetrics.length; i++) {
      totalChange += Math.abs(stageMetrics[i].meanRT - stageMetrics[i - 1].meanRT);
    }
    stageTransitionEffect = totalChange / (stageMetrics.length - 1);
  }

  // Session fatigue: slope of ALL user RTs in chronological order
  const sessionFatigueSlope = linearSlope(allUserRTs);

  // Engagement ratio: proportion of substantive messages (>50 chars)
  const substantive = allUserMessageLengths.filter((l) => l > 50).length;
  const engagementRatio =
    allUserMessageLengths.length > 0 ? substantive / allUserMessageLengths.length : 0;

  return {
    stages: stageMetrics,
    automationBiasRisk,
    stageTransitionEffect,
    sessionFatigueSlope,
    engagementRatio,
    allUserRTs,
    allUserMessageLengths,
    allDeliberationTimes,
  };
}
