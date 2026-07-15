# ThinkHigher

ThinkHigher is a work simulation platform for practicing and assessing higher-order thinking. Students work through realistic, multi-stage workplace scenarios (e.g. a junior software engineer handling a bug report, or an analyst briefing an executive), talking to AI-driven stakeholders in text or voice. Each session is scored against a rubric and can produce a cognitive profile of the participant.

## Stack

- **Framework**: Next.js 16 (App Router, TypeScript, Tailwind CSS 4)
- **LLM**: Google Gemini (`gemini-2.5-flash` by default) — used for both stakeholder chat and speech-to-text transcription
- **Text-to-speech**: Amazon Polly
- **Auth**: NextAuth v5 (Google OAuth)
- **Database**: Vercel Postgres, via `drizzle-orm` — falls back to an in-memory store when unconfigured
- **Email**: Resend + `@react-email/components`
- **State machine**: XState (`@xstate/react`)
- **Testing**: Vitest + Testing Library + MSW
- **Hosting**: Vercel

## Getting started

```bash
npm install
cp .env.example .env.local   # fill in the values, see below
npm run dev                  # http://localhost:3000
```

> Use `http://localhost:3000`, not your machine's network IP — the microphone requires a secure context, and only `localhost` qualifies without HTTPS.

Other scripts:

```bash
npm run build         # production build
npm run start          # run the production build
npm run lint           # eslint
npm run test           # vitest, watch mode
npm run test:ci        # vitest, single run (used in CI)
npm run test:coverage  # vitest with coverage
```

CI (`.github/workflows/test.yml`) runs `npm run test:ci` on every push/PR to `main` and `dev`.

## APIs used & environment configuration

Copy `.env.example` to `.env.local` and fill in:

| Variable | Service | Required for |
|---|---|---|
| `GEMINI_API_KEY` | [Google AI Studio](https://aistudio.google.com/app/apikey) | Stakeholder chat (`/api/chat`) and speech-to-text (`/api/stt`, via Gemini multimodal transcription — no separate STT key) |
| `GEMINI_MODEL` | — | Optional override, defaults to `gemini-2.5-flash` |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_REGION` | Amazon Polly | Text-to-speech (`/api/tts`). IAM user needs `AmazonPollyReadOnlyAccess`. `us-east-1` recommended. |
| `AUTH_SECRET` | NextAuth v5 | Session auth. Generate with `openssl rand -base64 32`. |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google OAuth | Sign-in (`/api/auth/[...nextauth]`) |
| `POSTGRES_URL` | Vercel Postgres | Persisting sessions/transcripts/assessments. If unset, the app uses an in-memory store (`src/lib/db.ts`) — fine for local dev, but data doesn't survive a restart. |
| `RESEND_API_KEY` | Resend | Transactional email (`/api/email`) |

Without `GEMINI_API_KEY` the chat and STT routes return a clear 500 rather than failing silently. Everything else degrades gracefully (persistence failures never block the UX — see Conventions below).

Full endpoint list: `src/app/api/{chat,stt,tts,auth,sessions,evaluate,profile,compare,email}/route.ts`.

## How to add a new scenario

A scenario is a JSON file in `src/data/scenarios/` describing a sequence of stakeholder conversations ("stages"), each with an AI persona, turn limits, and an assessment rubric. There are two schema versions in use — pick based on complexity:

- **V1 ("Vela" style)** — one agent per stage, no shared agents across stages. See `src/data/scenarios/001-i-thought-it-worked.json` / `002-vela-sde-sim-001.json` and types in `src/lib/types.ts` (`ScenarioDefinition`, `StageDefinition`).
- **V2 ("Ridgeline" style)** — agents defined once in a top-level `agents` dict and referenced by ID from stages (needed when the same stakeholder appears in multiple stages), plus support for data-table/document artifacts and scripted `structuredProbes`. See `src/data/scenarios/003-ridgeline-analyst-sim-001.json`, types `SimulationV2`/`StageV2`, and the full schema rationale in `docs/design/simulation-schema-proposal.md`.

Steps to add a new scenario:

1. **Write the JSON** under `src/data/scenarios/NNN-your-scenario-id.json`, following one of the two schemas above. Key fields:
   - `assessmentConfig.skillDimensions` — the rubric dimensions scored at the end (originality, communication, etc.)
   - each stage's `agentProfile.personaPrompt` (V1) or `agents.<id>.personaPrompt` (V2) — the system prompt driving that stakeholder's behavior, written in-character with instructions on tone, what to probe for, and when to wrap up
   - `turnConfig` (`minTurns` / `maxTurns` / `wrapUpSignalTurn`) — controls how long the conversation runs before the agent naturally wraps up
   - `pollyVoice` per agent — must be a valid Amazon Polly voice ID (falls back to `"Joanna"` if omitted)
2. **Load it** — add a small loader module in `src/lib/` (mirror `src/lib/scenarios.ts` for V1 or `src/lib/scenarios-ridgeline.ts` for V2) that imports the JSON and exports the typed scenario plus any derived arrays (e.g. resolving `agentIds` to full agent objects for V2).
3. **Add a route** — create `src/app/simulations/<your-scenario-slug>/page.tsx` rendering `<Simulation />` (V1) or `<SimulationV2 />` (V2), pointed at your new loader.
4. **List it in the catalog** — add an entry to the `SIMULATIONS` array in `src/app/simulations/page.tsx` (id, href, title, description, duration, role, icon).
5. **If the stage has a video intro or an artifact** (HTML prototype, data table, document), add the video component under `src/components/` or the static artifact file under `public/mockups/`, and reference it via `videoComponent`/`artifactSrc` (V1) or `video.component`/`artifact.src` (V2).
6. **Test it end-to-end** — run `npm run dev`, walk through every stage, and confirm the assessment (`/api/evaluate`) produces sensible scores for the new rubric.

If you're touching the schema itself (not just authoring a new scenario), read `docs/design/simulation-schema-proposal.md` first — it documents the differences between V1/V2 and the reasoning behind each field before you add a third variant.

## Project structure

```
src/
  app/
    api/                # chat, stt, tts, auth, sessions, evaluate, profile, compare, email
    simulations/         # one route per scenario, catalog at simulations/page.tsx
    tasks/               # standalone cognitive tasks (bandit, ARC grid, etc.)
  components/            # Simulation.tsx (V1), SimulationV2.tsx, speech/voice UI, catalog cards
  data/scenarios/         # scenario JSON definitions
  hooks/                  # useSpeechInput / useSpeechOutput
  lib/
    types.ts             # all TypeScript types (scenario, chat, persistence, survey, profile)
    scenarios.ts / scenarios-ridgeline.ts   # scenario loaders
    db.ts / db-postgres.ts                 # persistence layer (in-memory or Postgres)
    rt-metrics.ts         # response-time metrics / cognitive signals
    centaur.ts            # Centaur behavioral prediction integration
    gecco.ts              # GeCCo cognitive model generation pipeline
    participant.ts         # Prolific ID passthrough + device metadata
docs/
  dev.md                  # environment setup + changelog of major features
  design/                 # schema proposals, architecture notes
  research/               # verified references for the cognitive-modeling roadmap
```

## Conventions

- Persistence failures never block the user experience — session/transcript writes are fire-and-forget.
- Scenario JSON is written to be Deliberate Lab-compatible (`turnConfig`, `channelType`, `agentProfile`/`agents`).
- Response time is tracked per message (`TranscriptEntry.responseTimeMs`) for cognitive profiling.
- Hierarchical Bayesian models (planned cognitive-modeling work) use non-centered parameterization.
- The brand name is "ThinkHigher" — not "ThinkWith" or other variants.

## Contributing

- New scenarios are the easiest way to contribute — see [How to add a new scenario](#how-to-add-a-new-scenario) above.

## Citation

If you use ThinkHigher in academic or research work, please cite it as:

```bibtex
@software{thinkhigher,
  title  = {ThinkHigher: A Simulation Platform for Higher-Order Thinking Assessment},
  author = {Gong, Jiachen and Hugh, Morgan and Ching, Joseph},
  year   = {2026},
  url    = {https://github.com/m9h/Thinking-Higher}
}
```
