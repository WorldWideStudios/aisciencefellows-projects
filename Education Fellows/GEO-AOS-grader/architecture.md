# GEO Grader — Architecture

## Repository Layout

```
/
├── frontend/          Next.js 15 App Router (TypeScript, Tailwind CSS)
├── backend/           FastAPI Python (AEO Grader only — not touched by Agent Operability work)
├── playwright-service/ Express skeleton for future browser checks (see below)
├── docker-compose.yml
└── SPEC.md            Original AEO Grader product spec
```

## Tech Stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 15 App Router, TypeScript strict mode |
| Styling | Tailwind CSS (custom components only — no shadcn, no MUI) |
| Charts | Recharts (AEO Grader only) |
| Tests | Vitest |
| Backend (AEO Grader) | FastAPI Python, PostgreSQL |
| Playwright service | Express (Node), port 3001 |

## Agent Operability Report — Key Architecture Decisions

| Decision | Choice |
|---|---|
| Backend | Next.js API routes only. Zero Python backend changes. |
| Data persistence | Re-scan on every page load. No DB, no cache. |
| Loading UX | SSE streaming — blocks arrive as they complete, not a fake timer. |
| SSE mechanism | `fetch` + `ReadableStream` (POST body needed; EventSource is GET-only). |
| Playwright / browser checks | Separate Express service at `/playwright-service/`; mock in MVP. |

## File Structure

```
frontend/
  app/
    agent-report/
      page.tsx                  ← landing (server component)
      AgentReportForm.tsx        ← "use client" form, navigates to /[domain]
      [domain]/
        page.tsx                 ← "use client", POSTs to API, reads SSE stream
        loading.tsx              ← static skeleton (shown during Next.js hydration)
    api/
      agent-check/
        route.ts                 ← POST, streams SSE, rate-limits by IP

  lib/agent-check/
    types.ts                     ← ALL TypeScript types (CheckResult, BlockResult,
    |                               AgentCheckResponse, SSEEvent, BrowserOperabilityResult)
    utils.ts                     ← fetchWithTimeout, normalizeUrl, checkRateLimit
    scoring.ts                   ← getGrade(score) → { grade, gradeColor }
    machine-interface.ts         ← Block 1: MCP, OpenAPI spec, coverage, public API
    browser-operability.ts       ← Block 2: callBrowserService() stub
    agent-discovery.ts           ← Block 3: llms.txt, robots.txt AI bots, schema.org, SDK
    auth-security.ts             ← Block 4: OAuth well-known, API keys, CORS
    index.ts                     ← runAgentCheck(url, domain, send) — parallel orchestrator

  components/agent-report/      ← see design.md for component descriptions

playwright-service/
  src/
    types.ts                     ← BrowserOperabilityResult, ScanRequest
    index.ts                     ← Express, POST /scan returns mock, GET /health
  Dockerfile                     ← node:20-slim, port 3001
```

## SSE Event Protocol

The API route (`/api/agent-check`) streams these events as each block resolves:

```typescript
// Emitted as each parallel block resolves:
{ type: "block", block: "machineInterface" | "browserOperability" | "agentDiscovery" | "authSecurity", result: BlockResult }

// After all 4 blocks settle:
{ type: "complete", result: AgentCheckResponse }

// On unrecoverable error during scan (bad URL, timeout):
{ type: "error", message: string }
// Note: rate limit (HTTP 429) is returned before the stream opens, not as an SSE event
```

Each SSE line format: `data: <JSON>\n\n`

## API Route Behaviour

- **Rate limit:** 10 scans/IP/hour. In-memory Map (resets on cold start). Exceeding → HTTP 429, no stream opened.
- **Total timeout:** 30s via `Promise.race` against a timeout sentinel inside the orchestrator.
- **Per-check timeout:** 8s (default in `fetchWithTimeout`).
- **User-Agent for outbound requests:** `AgentReadinessBot/1.0 (compatible; ${NEXT_PUBLIC_SITE_URL}/agent-report)`
- **Error handling:** each check is wrapped in try/catch; failure = `score: 0` for that check, scan continues.
- **`export const dynamic = "force-dynamic"`** on the route to prevent Vercel caching.

## Check Module Rules

- `checkMachineInterface`, `checkAgentDiscovery`, `checkAuthSecurity` all import `fetchWithTimeout` from `utils.ts`. Mock it with `vi.mock("../utils", ...)` in tests.
- `callBrowserService` reads `process.env.PLAYWRIGHT_SERVICE_URL`. If unset → returns mock immediately. If set → POSTs to `${PLAYWRIGHT_SERVICE_URL}/scan`. Either way, **always returns `status: "pending"`** (feature flag until V1.0).
- No `any` TypeScript anywhere. Block-specific fields (e.g. `allowedBots`, `percentage`, `policy`) are added via intersection types in each module, not on the base `CheckResult`.

## Block 2 Status Clarification

The Playwright service returns `status: "complete"` in its response (indicating "I ran successfully"). `callBrowserService()` ignores this and always sets `status: "pending"` on the returned `BlockResult`. The "pending" means "this feature is not yet live," not "the HTTP call failed."

## Environment Variables (frontend)

```
PLAYWRIGHT_SERVICE_URL=       # http://playwright:3001 in Docker; blank = mock
NEXT_PUBLIC_SITE_URL=         # https://your-domain.com; used in User-Agent header
NEXT_PUBLIC_API_URL=          # http://localhost:8000; points to Python backend (AEO Grader only)
```

## Robots.txt Scoring Thresholds

7 AI bots tracked: `anthropic-ai`, `gpt-bot`, `claude-bot`, `perplexity-bot`, `cohere-ai`, `google-extended`, `amazonbot`.

- Un-mentioned = allowed by default
- Wildcard `User-agent: *` with `Disallow: /` = all blocked (unless individually excepted)
- All 7 allowed → 6 pts
- ≥5 allowed (1–2 blocked) → 4 pts
- 3–4 blocked → 2 pts
- ≥5 blocked → 0 pts

## AEO Grader (existing feature)

Measures AI search visibility: takes a brand URL, generates 10 search queries, runs them through Perplexity Sonar Pro via OpenRouter, returns a Score 0–100 based on citation rate and mention rate.

- Frontend routes: `/` (landing), `/analyze/[id]` (confirmation form), `/report/[id]` (report)
- Backend: FastAPI Python at `http://localhost:8000`, PostgreSQL for persistence
- All LLM calls go through OpenRouter (`OPENROUTER_API_KEY` in `backend/.env`)
- **Do not modify the Python backend or any existing frontend files** when working on Agent Operability features.
