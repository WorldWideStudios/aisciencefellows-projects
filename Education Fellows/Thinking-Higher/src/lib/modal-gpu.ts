// --- Modal.com On-Demand GPU Integration ---
// Modal provides serverless GPU compute. We use it for:
//   1. Centaur inference (Llama 3.1 70B with LoRA adapter, needs A100 80GB)
//   2. Future JAX-based cognitive model fitting (NivStan-style Bayesian models)
//
// Architecture:
//   - Modal functions are defined in Python and deployed as web endpoints
//   - This TypeScript module calls those endpoints from Next.js API routes
//   - Modal cold-starts in ~30s for GPU containers; warm containers respond in <5s
//   - Cost: ~$3.58/hr for A100 80GB, billed per-second
//
// Setup:
//   1. pip install modal
//   2. modal setup (authenticate)
//   3. Deploy the Python functions (see modal_functions/ directory)
//   4. Set MODAL_ENDPOINT_URL in .env

export interface ModalConfig {
  endpointUrl: string;
  authToken: string;
  timeoutMs: number;
}

const DEFAULT_CONFIG: ModalConfig = {
  endpointUrl: process.env.MODAL_ENDPOINT_URL || "",
  authToken: process.env.MODAL_AUTH_TOKEN || "",
  timeoutMs: 120000, // 2 min for cold starts
};

export interface ModalInferenceRequest {
  task: "centaur-predict" | "gecco-fit" | "rt-model-fit";
  payload: Record<string, unknown>;
}

export interface ModalInferenceResponse {
  result: Record<string, unknown>;
  gpuTimeMs: number;
  cold_start: boolean;
}

// Call a Modal.com GPU endpoint.
// Returns null if Modal is not configured (graceful degradation).
export async function callModal(
  request: ModalInferenceRequest,
  config: ModalConfig = DEFAULT_CONFIG
): Promise<ModalInferenceResponse | null> {
  if (!config.endpointUrl) return null;

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), config.timeoutMs);

  try {
    const res = await fetch(config.endpointUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
      },
      body: JSON.stringify(request),
      signal: controller.signal,
    });

    clearTimeout(timeout);

    if (!res.ok) {
      console.error(`Modal GPU error: ${res.status}`);
      return null;
    }

    return await res.json();
  } catch (err) {
    clearTimeout(timeout);
    console.error("Modal GPU call failed:", err);
    return null;
  }
}

// --- Centaur via Modal ---

export async function centaurPredictViaModal(
  prompt: string,
  config: ModalConfig = DEFAULT_CONFIG
): Promise<ModalInferenceResponse | null> {
  return callModal(
    {
      task: "centaur-predict",
      payload: {
        prompt,
        max_new_tokens: 50,
        temperature: 1.0, // Centaur uses temp=1 to match human variability
      },
    },
    config
  );
}

// --- JAX Cognitive Model Fitting via Modal ---
// Replaces NivStan (Stan) with JAX-based implementation using NumPyro/Blackjax.
// Models: Rescorla-Wagner Q-learning, drift-diffusion, hierarchical Bayesian.

export async function fitCognitiveModelViaModal(
  modelType: "rescorla-wagner" | "drift-diffusion" | "hierarchical-bayesian",
  rtData: number[],
  choiceData: number[],
  config: ModalConfig = DEFAULT_CONFIG
): Promise<ModalInferenceResponse | null> {
  return callModal(
    {
      task: "rt-model-fit",
      payload: {
        model_type: modelType,
        rt_data: rtData,
        choice_data: choiceData,
        num_warmup: 500,
        num_samples: 1000,
      },
    },
    config
  );
}

// --- GeCCo Model Evaluation via Modal ---
// Execute LLM-generated Python cognitive model code in a sandboxed GPU environment.

export async function evaluateGeCCoModelViaModal(
  modelCode: string,
  behavioralData: Record<string, number[]>,
  config: ModalConfig = DEFAULT_CONFIG
): Promise<ModalInferenceResponse | null> {
  return callModal(
    {
      task: "gecco-fit",
      payload: {
        model_code: modelCode,
        behavioral_data: behavioralData,
      },
    },
    config
  );
}
