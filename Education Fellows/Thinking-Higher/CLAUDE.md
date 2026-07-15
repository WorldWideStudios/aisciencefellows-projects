# ThinkHigher — Claude Code Project Instructions

## What This Is
Cognitive simulation platform for higher-order thinking assessment. Currently a workplace simulation with 3 AI-driven stakeholder conversations. Long-term vision: cognitive security research platform with game-theoretic scenarios, RT-based profiling, and computational cognitive modeling.

## Stack
- **Framework**: Next.js 16 (App Router, TypeScript, Tailwind)
- **LLM**: Gemini 2.5 Flash via `src/app/api/chat/route.ts` (key never exposed to client)
- **Hosting**: Vercel
- **Cognitive modeling stack (planned)**: JAX + NumPyro + pyhgf, served via Modal.com GPU

## Key Paths
- `src/data/scenarios/` — Scenario definitions as JSON
- `src/lib/scenarios.ts` — Imports JSON, exports `STAGES[]` + `SCENARIO`
- `src/lib/types.ts` — All TypeScript types (scenario, chat, persistence, survey, profile)
- `src/lib/db.ts` — DB interface (in-memory Map, swap for Vercel Postgres later)
- `src/lib/rt-metrics.ts` — Response time metrics + cognitive signals
- `src/lib/centaur.ts` — Centaur behavioral prediction integration
- `src/lib/gecco.ts` — GeCCo cognitive model generation pipeline
- `src/lib/participant.ts` — Prolific ID passthrough + device metadata
- `src/components/Simulation.tsx` — Main simulation component
- `src/app/api/sessions/route.ts` — Session/transcript/assessment persistence
- `src/app/api/profile/route.ts` — Cognitive profile computation endpoint

## Research Documentation
See `docs/research/` for verified references and integration plans:
- `cognitive-modeling.md` — Centaur, GeCCo, Psych-101, Minimap, Welfare Diplomacy
- `comp-psychiatry-tools.md` — CPC Zurich: pyhgf, hBayesDM, HMeta-d, BlackJAX, HDDM
- `hbayesdm-models.md` — Full Stan model math for JAX port (RW, DDM, RL+DDM)
- `nivlab-resources.md` — NivTurk, jsPsych demos, OpenCogData, NivStan
- `gemini-project-vision.md` — Games, RT profiling, agent experiments, microworlds

## Conventions
- Brand name is "ThinkHigher" (not "ThinkWith")
- Persistence failures never block the UX (fire-and-forget pattern)
- Scenarios use Deliberate Lab-compatible fields (turnConfig, channelType, agentProfile)
- RT tracked per message in TranscriptEntry for cognitive profiling
- Non-centered parameterization for all hierarchical Bayesian models

## Owner
- GitHub: m9h
- Email: morgan.hough@gmail.com
