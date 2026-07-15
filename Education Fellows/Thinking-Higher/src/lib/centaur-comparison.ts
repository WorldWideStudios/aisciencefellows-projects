// --- Centaur Comparison Pipeline ---
// Compares participant choices against Centaur's predicted human behavior
// using negative log-likelihood (NLL), the primary evaluation metric from
// Binz et al., Nature 2025.
//
// Centaur NLL benchmarks (from the paper, averaged across experiments):
//   Centaur:            0.44
//   Llama 3.1 70B:      0.58
//   Domain-specific:     0.56
//   Random (2-choice):   0.693
//
// Two modes:
//   ONLINE  — calls the Centaur API endpoint for real next-token probabilities
//   OFFLINE — uses a Rescorla-Wagner softmax surrogate (domain-specific baseline)

import type {
  BanditTrialData,
  TwoStepTrialData,
  TaskSummary,
} from "@/lib/types";
import { fitRW, rwLogLikelihood } from "@/lib/models/rescorla-wagner";
import { predictWithCentaur } from "@/lib/centaur";
import {
  formatBanditPrefix,
  formatTwoStepPrefix,
  getChoiceToken,
  parseChoiceProbabilities,
} from "@/lib/psych101-format";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface CentaurTrialPrediction {
  trialIndex: number;
  /** Predicted probability of the actual choice */
  pActual: number;
  /** Predicted probability distribution over all choices */
  pDistribution: Record<string, number>;
  /** Negative log-likelihood for this trial */
  nll: number;
  /** What the participant actually chose (token) */
  actualChoice: string;
  /** What Centaur predicted as most likely */
  predictedChoice: string;
}

export interface CentaurComparisonResult {
  taskType: string;
  /** Mean NLL across all trials (the paper's primary metric) */
  meanNLL: number;
  /** Per-trial predictions */
  trials: CentaurTrialPrediction[];
  /** Accuracy: fraction of trials where Centaur's top prediction matched actual */
  predictionAccuracy: number;
  /** For comparison: random baseline NLL */
  randomBaselineNLL: number;
  /** RW model NLL for comparison (if bandit) */
  rwModelNLL?: number;
  /** Total time for all Centaur calls */
  totalLatencyMs: number;
}

// ---------------------------------------------------------------------------
// Random baseline
// ---------------------------------------------------------------------------

/**
 * Compute random baseline NLL.
 * For 2-choice: -log(0.5) = 0.693 per trial
 * For 3-choice: -log(0.333) = 1.099 per trial
 */
export function computeRandomBaselineNLL(numChoices: number): number {
  if (numChoices <= 0) return 0;
  return -Math.log(1 / numChoices);
}

// ---------------------------------------------------------------------------
// RW baseline
// ---------------------------------------------------------------------------

/**
 * Compute RW model NLL for comparison.
 * Uses best-fit alpha/tau from grid search.
 * This is the "domain-specific cognitive model" baseline from the paper.
 */
export function computeRWBaselineNLL(trials: BanditTrialData[]): {
  nll: number;
  alpha: number;
  tau: number;
} {
  if (trials.length === 0) {
    return { nll: 0, alpha: 0, tau: 0 };
  }

  const fit = fitRW(trials);

  // fitRW returns total log-likelihood (negative closer to 0 = better fit).
  // We need mean NLL = -totalLL / N.
  const meanNLL = -fit.logLikelihood / trials.length;

  return {
    nll: meanNLL,
    alpha: fit.alpha,
    tau: fit.tau,
  };
}

// ---------------------------------------------------------------------------
// Offline RW surrogate predictions
// ---------------------------------------------------------------------------

/**
 * Compute softmax choice probabilities for a single bandit trial under RW model.
 * Returns P(arm) for each arm given current Q-values and temperature.
 */
function rwSoftmaxProbabilities(
  qValues: [number, number],
  tau: number
): Record<string, number> {
  const expQ0 = Math.exp(tau * qValues[0]);
  const expQ1 = Math.exp(tau * qValues[1]);
  const sumExp = expQ0 + expQ1;

  return {
    B: expQ0 / sumExp,
    C: expQ1 / sumExp,
  };
}

/**
 * Generate per-trial RW surrogate predictions for the bandit task.
 * Simulates what a domain-specific cognitive model would predict at each trial.
 */
function rwSurrogatePredictions(
  trials: BanditTrialData[],
  alpha: number,
  tau: number,
  skipFirst: number
): CentaurTrialPrediction[] {
  const predictions: CentaurTrialPrediction[] = [];
  let Q: [number, number] = [0.5, 0.5];

  for (let t = 0; t < trials.length; t++) {
    const trial = trials[t];

    if (t >= skipFirst) {
      const pDist = rwSoftmaxProbabilities(Q, tau);
      const actualToken = getChoiceToken("two-armed-bandit", trial.chosenArm);
      const pActual = Math.max(pDist[actualToken] ?? 1e-15, 1e-15);
      const nll = -Math.log(pActual);

      // Find the predicted (most likely) choice
      const predictedChoice = Object.entries(pDist).reduce(
        (best, [token, prob]) => (prob > best.prob ? { token, prob } : best),
        { token: "", prob: -1 }
      ).token;

      predictions.push({
        trialIndex: t,
        pActual,
        pDistribution: pDist,
        nll,
        actualChoice: actualToken,
        predictedChoice,
      });
    }

    // RW update (always, including skipped trials — they still inform Q)
    const chosen = trial.chosenArm;
    Q = [...Q] as [number, number];
    Q[chosen] = Q[chosen] + alpha * (trial.reward - Q[chosen]);
  }

  return predictions;
}

// ---------------------------------------------------------------------------
// Online Centaur predictions
// ---------------------------------------------------------------------------

/**
 * Call Centaur for a single bandit trial prediction.
 * Returns null if the call fails (caller should fall back to offline).
 */
async function centaurBanditTrialPrediction(
  trials: BanditTrialData[],
  trialIndex: number
): Promise<{
  prediction: CentaurTrialPrediction;
  latencyMs: number;
} | null> {
  const prefix = formatBanditPrefix(trials, trialIndex);
  const centaurResult = await predictWithCentaur(prefix);

  if (!centaurResult || !centaurResult.rawOutput) {
    return null;
  }

  const choiceTokens = ["B", "C"];
  const pDist = parseChoiceProbabilities(centaurResult.rawOutput, choiceTokens);
  const actualToken = getChoiceToken(
    "two-armed-bandit",
    trials[trialIndex].chosenArm
  );
  const pActual = Math.max(pDist[actualToken] ?? 1e-15, 1e-15);
  const nll = -Math.log(pActual);

  const predictedChoice = Object.entries(pDist).reduce(
    (best, [token, prob]) => (prob > best.prob ? { token, prob } : best),
    { token: "", prob: -1 }
  ).token;

  return {
    prediction: {
      trialIndex,
      pActual,
      pDistribution: pDist,
      nll,
      actualChoice: actualToken,
      predictedChoice,
    },
    latencyMs: centaurResult.latencyMs,
  };
}

/**
 * Call Centaur for a single two-step trial prediction (stage 1 choice only).
 * Returns null if the call fails.
 */
async function centaurTwoStepTrialPrediction(
  trials: TwoStepTrialData[],
  trialIndex: number
): Promise<{
  prediction: CentaurTrialPrediction;
  latencyMs: number;
} | null> {
  const prefix = formatTwoStepPrefix(trials, trialIndex);
  const centaurResult = await predictWithCentaur(prefix);

  if (!centaurResult || !centaurResult.rawOutput) {
    return null;
  }

  const choiceTokens = ["F", "V"];
  const pDist = parseChoiceProbabilities(centaurResult.rawOutput, choiceTokens);
  const actualToken = getChoiceToken(
    "two-step",
    trials[trialIndex].stage1Choice
  );
  const pActual = Math.max(pDist[actualToken] ?? 1e-15, 1e-15);
  const nll = -Math.log(pActual);

  const predictedChoice = Object.entries(pDist).reduce(
    (best, [token, prob]) => (prob > best.prob ? { token, prob } : best),
    { token: "", prob: -1 }
  ).token;

  return {
    prediction: {
      trialIndex,
      pActual,
      pDistribution: pDist,
      nll,
      actualChoice: actualToken,
      predictedChoice,
    },
    latencyMs: centaurResult.latencyMs,
  };
}

// ---------------------------------------------------------------------------
// Main comparison functions
// ---------------------------------------------------------------------------

/**
 * Run the full Centaur comparison pipeline for a bandit task.
 *
 * For each trial t:
 *   1. Build Psych-101 prefix from trials 0..t-1
 *   2. Call Centaur to get P(next choice | prefix)
 *   3. Record NLL = -log(P(actual choice))
 *
 * Returns aggregate comparison statistics.
 *
 * If CENTAUR_ENDPOINT is not configured, runs in OFFLINE MODE:
 *   - Uses the Rescorla-Wagner softmax model as a surrogate
 *   - Labels results as "RW-surrogate" not "Centaur"
 *   - Still useful for testing the pipeline
 */
export async function compareBanditWithCentaur(
  trials: BanditTrialData[],
  options?: {
    /** Skip first N trials (allow learning). Default: 5 */
    skipFirst?: number;
    /** Use offline RW surrogate instead of Centaur API */
    offline?: boolean;
    /** RW parameters to use in offline mode (default: fit from data) */
    rwParams?: { alpha: number; tau: number };
  }
): Promise<CentaurComparisonResult> {
  const skipFirst = options?.skipFirst ?? 5;
  const useOffline =
    options?.offline ?? !process.env.CENTAUR_ENDPOINT;

  const startTime = Date.now();
  let trialPredictions: CentaurTrialPrediction[];
  let totalLatencyMs = 0;

  if (useOffline) {
    // --- OFFLINE MODE: RW surrogate ---
    let alpha: number;
    let tau: number;

    if (options?.rwParams) {
      alpha = options.rwParams.alpha;
      tau = options.rwParams.tau;
    } else {
      const fit = fitRW(trials);
      alpha = fit.alpha;
      tau = fit.tau;
    }

    trialPredictions = rwSurrogatePredictions(trials, alpha, tau, skipFirst);
    totalLatencyMs = Date.now() - startTime;
  } else {
    // --- ONLINE MODE: Centaur API ---
    trialPredictions = [];

    for (let t = skipFirst; t < trials.length; t++) {
      const result = await centaurBanditTrialPrediction(trials, t);

      if (result) {
        trialPredictions.push(result.prediction);
        totalLatencyMs += result.latencyMs;
      } else {
        // Centaur call failed — fall back to RW surrogate for this trial
        const fit = fitRW(trials.slice(0, t));
        const fallback = rwSurrogatePredictions(
          trials.slice(0, t + 1),
          fit.alpha,
          fit.tau,
          t
        );
        if (fallback.length > 0) {
          trialPredictions.push(fallback[0]);
        }
      }
    }

    totalLatencyMs = totalLatencyMs || Date.now() - startTime;
  }

  // Compute aggregates
  const numChoices = 2;
  const randomBaselineNLL = computeRandomBaselineNLL(numChoices);
  const rwBaseline = computeRWBaselineNLL(trials);

  const meanNLL =
    trialPredictions.length > 0
      ? trialPredictions.reduce((sum, p) => sum + p.nll, 0) /
        trialPredictions.length
      : 0;

  const correctPredictions = trialPredictions.filter(
    (p) => p.predictedChoice === p.actualChoice
  ).length;
  const predictionAccuracy =
    trialPredictions.length > 0
      ? correctPredictions / trialPredictions.length
      : 0;

  return {
    taskType: useOffline ? "two-armed-bandit (RW-surrogate)" : "two-armed-bandit",
    meanNLL,
    trials: trialPredictions,
    predictionAccuracy,
    randomBaselineNLL,
    rwModelNLL: rwBaseline.nll,
    totalLatencyMs,
  };
}

/**
 * Run Centaur comparison for a two-step task.
 * Predicts stage 1 choices only (which spaceship).
 */
export async function compareTwoStepWithCentaur(
  trials: TwoStepTrialData[],
  options?: {
    /** Skip first N trials. Default: 5 */
    skipFirst?: number;
    /** Use offline mode (uniform surrogate — no domain-specific model for two-step) */
    offline?: boolean;
  }
): Promise<CentaurComparisonResult> {
  const skipFirst = options?.skipFirst ?? 5;
  const useOffline =
    options?.offline ?? !process.env.CENTAUR_ENDPOINT;

  const startTime = Date.now();
  let trialPredictions: CentaurTrialPrediction[];
  let totalLatencyMs = 0;

  if (useOffline) {
    // --- OFFLINE MODE ---
    // No RW surrogate for two-step (it would need a full model-based/model-free hybrid).
    // Use uniform prediction as the offline baseline.
    trialPredictions = [];
    const numChoices = 2;
    const uniformProb = 1 / numChoices;

    for (let t = skipFirst; t < trials.length; t++) {
      const trial = trials[t];
      const actualToken = getChoiceToken("two-step", trial.stage1Choice);
      const pDist: Record<string, number> = { F: uniformProb, V: uniformProb };
      const pActual = uniformProb;
      const nll = -Math.log(Math.max(pActual, 1e-15));

      trialPredictions.push({
        trialIndex: t,
        pActual,
        pDistribution: pDist,
        nll,
        actualChoice: actualToken,
        predictedChoice: "F", // Arbitrary for uniform — both equal
      });
    }

    totalLatencyMs = Date.now() - startTime;
  } else {
    // --- ONLINE MODE: Centaur API ---
    trialPredictions = [];

    for (let t = skipFirst; t < trials.length; t++) {
      const result = await centaurTwoStepTrialPrediction(trials, t);

      if (result) {
        trialPredictions.push(result.prediction);
        totalLatencyMs += result.latencyMs;
      } else {
        // Centaur call failed — fall back to uniform for this trial
        const actualToken = getChoiceToken("two-step", trials[t].stage1Choice);
        const uniformProb = 0.5;
        trialPredictions.push({
          trialIndex: t,
          pActual: uniformProb,
          pDistribution: { F: uniformProb, V: uniformProb },
          nll: -Math.log(uniformProb),
          actualChoice: actualToken,
          predictedChoice: "F",
        });
      }
    }

    totalLatencyMs = totalLatencyMs || Date.now() - startTime;
  }

  // Compute aggregates
  const numChoices = 2;
  const randomBaselineNLL = computeRandomBaselineNLL(numChoices);

  const meanNLL =
    trialPredictions.length > 0
      ? trialPredictions.reduce((sum, p) => sum + p.nll, 0) /
        trialPredictions.length
      : 0;

  const correctPredictions = trialPredictions.filter(
    (p) => p.predictedChoice === p.actualChoice
  ).length;
  const predictionAccuracy =
    trialPredictions.length > 0
      ? correctPredictions / trialPredictions.length
      : 0;

  return {
    taskType: useOffline ? "two-step (offline)" : "two-step",
    meanNLL,
    trials: trialPredictions,
    predictionAccuracy,
    randomBaselineNLL,
    totalLatencyMs,
  };
}
