// --- Centaur Integration ---
// Centaur: fine-tuned Llama 3.1 70B on Psych-101 (Nature 2025, Binz et al.)
// Predicts human-like behavioral responses given natural language task descriptions.
//
// Serving strategy (fastest path to real-time):
//   1. HuggingFace Inference Endpoints (dedicated A100, ~$4/hr)
//   2. Modal.com / Replicate on-demand GPU
//   3. Self-hosted vLLM with LoRA adapter
//
// Input format: natural language experiment description with choices marked <<choice>>
// Output: next-token probabilities over <<choice>> tokens = predicted human behavior

export interface CentaurPrediction {
  // Predicted probability distribution over response strategies
  predictions: Record<string, number>;
  // Raw model output for debugging
  rawOutput?: string;
  // Latency of the prediction call
  latencyMs: number;
}

export interface CentaurConfig {
  endpoint: string;       // Inference API URL
  apiKey: string;         // Auth token
  model: string;          // Model ID (default: marcelbinz/Llama-3.1-Centaur-70B-adapter)
  timeoutMs: number;
}

const DEFAULT_CONFIG: CentaurConfig = {
  endpoint: process.env.CENTAUR_ENDPOINT || "",
  apiKey: process.env.CENTAUR_API_KEY || "",
  model: process.env.CENTAUR_MODEL || "marcelbinz/Llama-3.1-Centaur-70B-adapter",
  timeoutMs: 30000,
};

// Format a ThinkHigher scenario stage as a Psych-101-style natural language transcript.
// Centaur expects experiment descriptions formatted like:
//   "You see [stimulus]. You press <<choice>>. The feedback is [outcome]."
// For conversational scenarios, we adapt to:
//   "Your colleague says: [message]. You respond: <<strategy>>."
export function formatForCentaur(
  stageName: string,
  stageDescription: string,
  aiMessage: string,
  responseStrategies: string[]
): string {
  const strategiesFormatted = responseStrategies
    .map((s) => `<<${s}>>`)
    .join(" or ");

  return [
    `You are a participant in a workplace communication study.`,
    `In this stage, "${stageName}": ${stageDescription}`,
    `Your colleague says: "${aiMessage}"`,
    `How do you respond? You choose: ${strategiesFormatted}`,
  ].join("\n");
}

// Classify a user's actual response into a strategy category.
// This is needed to compare real behavior against Centaur predictions.
export function classifyResponseStrategy(
  userMessage: string,
  stageId: string
): string {
  const lower = userMessage.toLowerCase();
  const len = userMessage.length;

  // Simple heuristic classification — will be replaced by LLM classification
  if (lower.includes("?")) {
    if (lower.includes("why") || lower.includes("how") || lower.includes("what if"))
      return "deep-probe";
    return "clarifying-question";
  }
  if (lower.includes("sorry") || lower.includes("apologize") || lower.includes("my fault"))
    return "ownership-apology";
  if (lower.includes("i think") || lower.includes("i can") || lower.includes("let me"))
    return "proactive-ownership";
  if (len < 30) return "brief-acknowledgment";
  return "substantive-response";
}

// Call the Centaur model to get behavioral predictions.
// Returns null if Centaur is not configured (graceful degradation).
export async function predictWithCentaur(
  prompt: string,
  config: CentaurConfig = DEFAULT_CONFIG
): Promise<CentaurPrediction | null> {
  if (!config.endpoint || !config.apiKey) return null;

  const start = Date.now();

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), config.timeoutMs);

    const res = await fetch(config.endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${config.apiKey}`,
      },
      body: JSON.stringify({
        inputs: prompt,
        parameters: {
          max_new_tokens: 50,
          return_full_text: false,
          details: true,
        },
      }),
      signal: controller.signal,
    });

    clearTimeout(timeout);
    const data = await res.json();
    const latencyMs = Date.now() - start;

    // Parse token probabilities from the response
    // HuggingFace TGI returns top tokens with logprobs
    const rawOutput = typeof data === "string" ? data : JSON.stringify(data);

    return {
      predictions: {}, // Populated by parsing token logprobs in production
      rawOutput,
      latencyMs,
    };
  } catch {
    return null;
  }
}

// Compare a participant's actual behavior against Centaur's predicted distribution.
// Returns a "deviation score" — how far from the statistical human norm they are.
// Positive = more analytical than average. Negative = more impulsive than average.
export function computeCentaurDeviation(
  actualStrategy: string,
  prediction: CentaurPrediction
): number {
  const predictedProb = prediction.predictions[actualStrategy];
  if (predictedProb === undefined) return 0;

  // Deviation: how surprising was this choice?
  // Log-odds relative to most probable strategy
  const maxProb = Math.max(...Object.values(prediction.predictions));
  if (maxProb === 0) return 0;
  return Math.log(predictedProb / maxProb);
}
