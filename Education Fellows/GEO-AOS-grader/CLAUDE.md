# GEO Grader — Project Context for Claude

## Running the Project

```bash
# Full stack
docker-compose up

# Frontend only (dev mode with hot reload)
cd frontend && npm run dev        # http://localhost:3000

# Playwright service (mock, no Playwright installed yet)
cd playwright-service && npm run dev   # http://localhost:3001

# Tests
cd frontend && npm test
cd frontend && npx tsc --noEmit   # type check only
```

## Reference Docs

- [architecture.md](architecture.md) — repo layout, file structure, SSE protocol, API behaviour, env vars, check module rules
- [design.md](design.md) — UI design language, Tailwind patterns, component list, grade colors

---

## Agent Operability Report (primary feature being built)

**Route:** `/agent-report` (landing) and `/agent-report/[domain]` (results)

**What it measures:** Whether AI agents can *interact* with a platform — MCP servers, OpenAPI specs, OAuth, CORS, llms.txt, robots.txt permissions, Schema.org markup, SDK docs. Distinct from the AEO Grader which measures AI *visibility*.

### Scoring

**Total: 0–100 points across 4 blocks**

| Block | Max pts | MVP |
|---|---|---|
| Machine Interface | 30 | Full |
| Browser Operability | 25 | Stub — always 0 / "pending" |
| Agent Discovery | 25 | Full |
| Auth & Security | 20 | Full |

Grade colors are defined in `frontend/lib/agent-check/scoring.ts` — see [design.md](design.md) for values.

---

## AEO Grader (existing feature — brief context)

The other tool on this site. Measures AI search visibility via Perplexity Sonar Pro / OpenRouter.

- **Do not modify the Python backend or any existing frontend files** when working on Agent Operability features.

See [architecture.md](architecture.md) for full AEO Grader stack details.

---

## Implementation Plans & Specs

Agent Operability Report — feature plan:
`docs/superpowers/plans/2026-05-28-agent-operability-report.md`

Agent Operability Report — original design spec:
`docs/superpowers/specs/2026-05-28-agent-operability-report-design.md`

Hybrid Two-Phase Checking — scoring accuracy redesign spec (current):
`docs/superpowers/specs/2026-05-28-hybrid-two-phase-checking-design.md`
