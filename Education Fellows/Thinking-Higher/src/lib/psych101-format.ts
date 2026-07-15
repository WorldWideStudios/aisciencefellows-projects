// --- Psych-101 Transcript Formatter ---
// Converts ThinkHigher cognitive task trial data into the exact natural language
// format used by Centaur (Binz et al., Nature 2025). Centaur was trained on the
// Psych-101 dataset where every experiment is a natural language transcript with
// human choices marked by << >> tokens.
//
// Reference: https://github.com/marcelbinz/Psych-101
// Key detail: Centaur predicts the next token after "You press <<" — so prefix
// transcripts must end at exactly that boundary for valid next-choice prediction.

import type {
  BanditTrialData,
  TwoStepTrialData,
  ReversalTrialData,
} from "@/lib/types";

// ---------------------------------------------------------------------------
// Constants: label mappings matching Psych-101 conventions
// ---------------------------------------------------------------------------

/** Two-armed bandit arm labels. Arm 0 = B, arm 1 = C. */
const BANDIT_ARM_LABELS = ["B", "C"] as const;

/** Three-armed bandit (reversal) arm labels. Arm 0 = B, arm 1 = C, arm 2 = D. */
const REVERSAL_ARM_LABELS = ["B", "C", "D"] as const;

/** Two-step task: stage 1 spaceship labels. Choice 0 = F, choice 1 = V. */
const SPACESHIP_LABELS = ["F", "V"] as const;

/** Two-step task: planet labels by stage2 state. State 0 = M, state 1 = S. */
const PLANET_LABELS = ["M", "S"] as const;

/** Two-step task: alien labels per planet. State 0 → [G, W], state 1 → [R, T]. */
const ALIEN_LABELS: Record<0 | 1, readonly [string, string]> = {
  0: ["G", "W"],
  1: ["R", "T"],
};

// ---------------------------------------------------------------------------
// Preambles: exact strings matching Psych-101 training data
// ---------------------------------------------------------------------------

const BANDIT_PREAMBLE =
  "In this task, you have to repeatedly choose between two slot machines labeled B and C. " +
  "When you select one of the machines, you will win or lose points. " +
  "Your goal is to choose the slot machine that will give you the most points.";

const TWO_STEP_PREAMBLE =
  "You will be taking one of the spaceships F or V to one of the planets M or S. " +
  "When you arrive at each planet, you will ask one of the aliens for space treasure.";

const REVERSAL_PREAMBLE =
  "In this task, you have to repeatedly choose between three slot machines labeled B, C, and D. " +
  "When you select one of the machines, you will win or lose points. " +
  "Your goal is to choose the slot machine that will give you the most points.";

// ---------------------------------------------------------------------------
// Bandit formatting
// ---------------------------------------------------------------------------

/**
 * Format a single bandit trial line in Psych-101 style.
 * Example: "You press <<C>> and get 1 points."
 */
function formatBanditTrial(trial: BanditTrialData): string {
  const armLabel = BANDIT_ARM_LABELS[trial.chosenArm];
  return `You press <<${armLabel}>> and get ${trial.reward} points.`;
}

/**
 * Format bandit trials into a complete Psych-101 style transcript.
 * Uses arm labels B and C (matching Psych-101 convention).
 * Points are 1 (reward) or 0 (no reward).
 */
export function formatBanditTranscript(trials: BanditTrialData[]): string {
  const lines = [BANDIT_PREAMBLE, ...trials.map(formatBanditTrial)];
  return lines.join("\n");
}

/**
 * Format a prefix of bandit trials for incremental prediction.
 * Returns transcript up to trial N, ending with the stimulus prompt
 * but NOT the choice — so Centaur predicts the next choice.
 *
 * The transcript includes:
 *   - Preamble
 *   - Trials 0 through upToTrial - 1 (complete, with choices and rewards)
 *   - An incomplete final line: "You press <<"
 *
 * Centaur then completes the << token with the predicted arm label.
 */
export function formatBanditPrefix(
  trials: BanditTrialData[],
  upToTrial: number
): string {
  const completedTrials = trials.slice(0, upToTrial);
  const lines = [
    BANDIT_PREAMBLE,
    ...completedTrials.map(formatBanditTrial),
    "You press <<",
  ];
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Two-step task formatting
// ---------------------------------------------------------------------------

/**
 * Format a single two-step trial in Psych-101 style.
 *
 * Example:
 *   You are presented with spaceships V and F.
 *   You press <<V>>. You end up on planet M and see aliens G and W. You press <<G>>.
 *   You find 1 piece of space treasure.
 */
function formatTwoStepTrial(trial: TwoStepTrialData): string {
  const ship = SPACESHIP_LABELS[trial.stage1Choice];
  const planet = PLANET_LABELS[trial.stage2State];
  const aliens = ALIEN_LABELS[trial.stage2State];
  const alien = aliens[trial.stage2Choice];

  const line1 = "You are presented with spaceships V and F.";
  const line2 =
    `You press <<${ship}>>. ` +
    `You end up on planet ${planet} and see aliens ${aliens[0]} and ${aliens[1]}. ` +
    `You press <<${alien}>>.`;
  const line3 = `You find ${trial.reward} piece of space treasure.`;

  return `${line1}\n${line2}\n${line3}`;
}

/**
 * Format two-step task trials into a complete Psych-101 style transcript.
 * Uses spaceship/planet cover story matching Psych-101 convention.
 *
 * Stage 1 options: spaceships F and V (choice 0 = F, choice 1 = V)
 * Stage 2 state 0: planet M, aliens G and W
 * Stage 2 state 1: planet S, aliens R and T
 */
export function formatTwoStepTranscript(trials: TwoStepTrialData[]): string {
  const lines = [TWO_STEP_PREAMBLE, ...trials.map(formatTwoStepTrial)];
  return lines.join("\n");
}

/**
 * Format two-step prefix for incremental prediction.
 * Ends at stage 1 choice prompt (predicting which spaceship).
 *
 * The transcript includes:
 *   - Preamble
 *   - Trials 0 through upToTrial - 1 (complete)
 *   - "You are presented with spaceships V and F."
 *   - "You press <<"
 *
 * Centaur then completes with the predicted spaceship label.
 */
export function formatTwoStepPrefix(
  trials: TwoStepTrialData[],
  upToTrial: number
): string {
  const completedTrials = trials.slice(0, upToTrial);
  const lines = [
    TWO_STEP_PREAMBLE,
    ...completedTrials.map(formatTwoStepTrial),
    "You are presented with spaceships V and F.",
    "You press <<",
  ];
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Reversal learning formatting
// ---------------------------------------------------------------------------

/**
 * Format a single reversal learning trial line in Psych-101 style.
 * Example: "You press <<D>> and get 1 points."
 */
function formatReversalTrial(trial: ReversalTrialData): string {
  const armLabel = REVERSAL_ARM_LABELS[trial.chosenArm];
  return `You press <<${armLabel}>> and get ${trial.reward} points.`;
}

/**
 * Format reversal learning trials (3-arm bandit) into a complete Psych-101 transcript.
 * Uses arm labels B, C, and D.
 */
export function formatReversalTranscript(trials: ReversalTrialData[]): string {
  const lines = [REVERSAL_PREAMBLE, ...trials.map(formatReversalTrial)];
  return lines.join("\n");
}

// ---------------------------------------------------------------------------
// Choice token utilities
// ---------------------------------------------------------------------------

/** Maps task type to an ordered array of choice token labels. */
const CHOICE_TOKEN_MAP: Record<string, readonly string[]> = {
  "two-armed-bandit": BANDIT_ARM_LABELS,
  "reversal-learning": REVERSAL_ARM_LABELS,
  "two-step": SPACESHIP_LABELS,
};

/**
 * Get the choice token that Centaur should predict.
 *
 * For bandits: "B" or "C" (arm 0 or 1)
 * For reversal: "B", "C", or "D" (arm 0, 1, or 2)
 * For two-step: "F" or "V" (stage 1 choice 0 or 1)
 *
 * @throws {Error} if taskType is unknown or choice index is out of range
 */
export function getChoiceToken(taskType: string, choice: number): string {
  const tokens = CHOICE_TOKEN_MAP[taskType];
  if (!tokens) {
    throw new Error(`Unknown task type for choice token mapping: ${taskType}`);
  }
  if (choice < 0 || choice >= tokens.length) {
    throw new Error(
      `Choice index ${choice} out of range for task type ${taskType} (valid: 0-${tokens.length - 1})`
    );
  }
  return tokens[choice];
}

// ---------------------------------------------------------------------------
// Centaur response parsing
// ---------------------------------------------------------------------------

/**
 * Parse a Centaur response to extract predicted probabilities over choice tokens.
 *
 * Centaur (via HuggingFace TGI / vLLM) returns logprobs for the top-k tokens.
 * This function extracts the probabilities for the specified choice tokens
 * (e.g., "B" and "C") and normalizes them into a distribution.
 *
 * Supports two response formats:
 *   1. HuggingFace TGI `details.top_tokens` / `details.prefill` format
 *   2. Raw JSON with a `tokens` array containing `{text, logprob}` objects
 *
 * If no choice tokens are found in the output, returns uniform probabilities.
 *
 * @param rawOutput - The raw JSON string from the model endpoint
 * @param choiceTokens - The set of valid choice tokens (e.g., ["B", "C"])
 * @returns A record mapping each choice token to its predicted probability
 */
export function parseChoiceProbabilities(
  rawOutput: string,
  choiceTokens: string[]
): Record<string, number> {
  const result: Record<string, number> = {};

  // Initialize all tokens to 0
  for (const token of choiceTokens) {
    result[token] = 0;
  }

  try {
    const data = JSON.parse(rawOutput);

    // Try HuggingFace TGI format: [{generated_text, details: {top_tokens: [[{text, logprob}]]}}]
    const topTokens = extractTopTokens(data);

    if (topTokens.length > 0) {
      // Find logprobs for our choice tokens in the first predicted position
      const firstPosition = topTokens[0];
      if (Array.isArray(firstPosition)) {
        for (const tokenInfo of firstPosition) {
          const text = (tokenInfo.text ?? tokenInfo.token ?? "").trim();
          if (choiceTokens.includes(text) && typeof tokenInfo.logprob === "number") {
            result[text] = Math.exp(tokenInfo.logprob);
          }
        }
      }
    }
  } catch {
    // If parsing fails, fall through to uniform distribution
  }

  // Normalize: if we found any probabilities, normalize them to sum to 1.
  // Otherwise, return uniform distribution.
  const total = Object.values(result).reduce((sum, p) => sum + p, 0);
  if (total > 0) {
    for (const token of choiceTokens) {
      result[token] = result[token] / total;
    }
  } else {
    // Uniform fallback
    const uniform = 1 / choiceTokens.length;
    for (const token of choiceTokens) {
      result[token] = uniform;
    }
  }

  return result;
}

/**
 * Extract top_tokens array from various HuggingFace / vLLM response formats.
 * Returns the top_tokens array (array of arrays of {text, logprob}), or [].
 */
function extractTopTokens(
  data: unknown
): Array<Array<{ text?: string; token?: string; logprob: number }>> {
  // Format 1: Array response [{generated_text, details: {top_tokens}}]
  if (Array.isArray(data) && data.length > 0) {
    const first = data[0];
    if (first?.details?.top_tokens) {
      return first.details.top_tokens;
    }
    // Some TGI versions use `tokens` instead of `top_tokens`
    if (first?.details?.tokens) {
      // Wrap single-level tokens array into the expected nested format
      return [first.details.tokens];
    }
  }

  // Format 2: Direct object {details: {top_tokens}}
  if (
    typeof data === "object" &&
    data !== null &&
    "details" in data
  ) {
    const details = (data as Record<string, unknown>).details;
    if (typeof details === "object" && details !== null) {
      if ("top_tokens" in details) {
        return (details as Record<string, unknown>).top_tokens as Array<
          Array<{ text?: string; token?: string; logprob: number }>
        >;
      }
      if ("tokens" in details) {
        return [(details as Record<string, unknown>).tokens as Array<{
          text?: string;
          token?: string;
          logprob: number;
        }>];
      }
    }
  }

  // Format 3: vLLM with choices[0].logprobs.content[0].top_logprobs
  if (
    typeof data === "object" &&
    data !== null &&
    "choices" in data
  ) {
    const choices = (data as Record<string, unknown>).choices;
    if (Array.isArray(choices) && choices.length > 0) {
      const logprobs = choices[0]?.logprobs?.content;
      if (Array.isArray(logprobs) && logprobs.length > 0) {
        const topLogprobs = logprobs[0]?.top_logprobs;
        if (Array.isArray(topLogprobs)) {
          // Convert vLLM format {token, logprob} to our expected format
          return [
            topLogprobs.map(
              (entry: { token: string; logprob: number }) => ({
                text: entry.token,
                logprob: entry.logprob,
              })
            ),
          ];
        }
      }
    }
  }

  return [];
}
