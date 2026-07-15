# Cognitive Modeling Resources (Verified)

## Centaur / Psych-101 (Binz et al., Nature 2025)

### Psych-101 Dataset
- **Paper**: "A foundation model to predict and capture human cognition" (Nature 2025)
- **Scale**: 160 experiments, 60,092 participants, 10,681,650 choices — numbers accurate
- **Hosted**: huggingface.co/datasets/marcelbinz/Psych-101
- **Format**: Natural language transcripts, NOT tabular CSV. Fields: `text`, `experiment`, `participant`
- **CRITICAL**: No response time (RT) data. Text transcripts only. Choices marked with `<<` `>>` tokens.
- **Successor**: Psych-201 under construction at github.com/marcelbinz/Psych-201

### Centaur Model
- **Architecture**: Fine-tuned Llama 3.1 70B via QLoRA
- **Open source**: Yes
  - Adapter weights: huggingface.co/marcelbinz/Llama-3.1-Centaur-70B-adapter
  - Code: github.com/marcelbinz/Llama-3.1-Centaur-70B
  - Project page: marcelbinz.github.io/centaur
- **Capabilities**: Predicts held-out human behavior better than domain-specific models. Generalizes to new tasks described in natural language. Internal representations align with human neural activity.
- **Hardware**: Requires 80GB GPU (A100) for local deployment
- **Input format**: Natural language experiment descriptions; choices as `<<choice>>` tokens

### Centaur Serving Strategy (for real-time inference)
Best path to real-time: merge LoRA into base, quantize to AWQ 4-bit (~35-40GB VRAM), serve via vLLM.
| Option | Latency | Cost | Notes |
|--------|---------|------|-------|
| Modal.com (A100) | ~30s cold, <5s warm | ~$3.58/hr | Best for on-demand. Already integrated in `modal-gpu.ts` |
| vLLM self-hosted (RunPod) | <5s | ~$2-4/hr | Best throughput, supports LoRA hot-loading |
| HF Inference Endpoints | <10s | ~$7-14/hr | Managed but expensive |
| Replicate.com | ~30-60s cold | ~$0.0035/sec | Pay-per-prediction |
| Quantized GGUF (consumer GPU) | Slower | Cheapest | Must merge LoRA first, 48GB GPU |

### How to use for ThinkHigher
- Describe our scenario stages in natural language → Centaur predicts what choices a "typical human" would make
- Use as benchmark: compare real participant behavior against Centaur baseline
- Cannot directly model RT (Psych-101 has no RT data) — we'd need our own RT profiling layer on top
- Integration code: `src/lib/centaur.ts` (HF/API), `src/lib/modal-gpu.ts` (Modal A100)

## JAX Reimplementation Plan (replacing NivStan/hBayesDM)
- Use **NumPyro** for NUTS/HMC sampling (JAX-native, same algorithm as Stan)
- Or **BlackJAX** for lower-level MCMC control
- Wiener first-passage time: implement via Navarro-Fuss approximation
- Full model math documented in `hbayesdm-models.md`
- Priority models: Rescorla-Wagner, DDM (choiceRT), RL+DDM combined (pstRT_rlddm1)
- Execute via Modal.com GPU for on-demand fitting

## GeCCo (Rmus et al., NeurIPS 2025 poster)

- **Paper**: "Generating Computational Cognitive Models using Large Language Models" (arXiv 2502.00879)
- **What it does**: Uses LLMs to generate **Python functions** (NOT Stan/PyMC) implementing cognitive models
- **Pipeline**: Task description + behavioral data + template function → LLM proposes model → fit to data → iterate
- **Domains**: Decision making, learning, planning, memory
- **Performance**: Matches or outperforms best domain-specific models from literature
- **No public repo** as of early 2026. Would need to implement pipeline from paper description.
- **Authors**: Milena Rmus (milenaccnlab.github.io), Akshay Jagadish, Eric Schulz

## DARPA ASIST / Minimap

- **Paper**: Nguyen & Gonzalez, "Minimap: An interactive dynamic decision making game for search and rescue missions" (Behavior Research Methods, Aug 2023)
- **What it is**: Browser-based 2D gridworld for dynamic decision-making research. Python (FastAPI) + JavaScript.
- **Open source**: github.com/DDM-Lab/MinimapInteractiveDDMGame
- **Human data**: github.com/DDM-Lab/HumanExperimentMinimap
- **Note**: Minimap is NOT the primary ASIST testbed (that was Minecraft-based). It's a complementary tool from CMU DDM-Lab.
- **ASIST data**: dataverse.asu.edu/dataverse/AptimaAsist

## Welfare Diplomacy (Mukobi et al., NeurIPS 2023 workshop)

- **Paper**: "Welfare Diplomacy: Benchmarking Language Model Cooperation" (arXiv 2310.08901)
- **Repo**: github.com/mukobi/welfare-diplomacy (541 commits, active)
- **What it is**: General-sum Diplomacy variant — players disband units for "Welfare Points"
- **LLM scaffolding**: Modular agents with OpenAI, Anthropic, Llama 2 backends
- **Deps**: Python 3.10-3.11, PyTorch, API keys, W&B

## Gemini Corrections Log
1. Psych-101 has NO RT data (Gemini implied it did)
2. GeCCo generates Python functions, NOT Stan/PyMC models
3. Minimap is 2D browser gridworld, not the Minecraft ASIST testbed
4. Welfare Diplomacy is workshop paper, not top-venue
5. "Stanford HAI Cognitive Security Task Force" — unverified, may be fabricated framing
