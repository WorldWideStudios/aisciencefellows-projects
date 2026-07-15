# Agent Operability Report — Design Spec
**Date:** 2026-05-28  
**Status:** Approved

---

## 1. Product Summary

Agent Operability Report is a new section inside the existing AEO Grader Next.js frontend. It answers: **"Can AI agents actually do things on this platform?"** — distinct from the AEO Grader which asks "can AI agents find this platform?"

Target audience: CTOs, Heads of Product, SaaS developers who want to understand their platform's readiness for agentic traffic.

MVP uses only static checks (HTTP requests, HTML/file parsing). No headless browser, no LLM calls, no Python backend changes. Deploys entirely on Vercel.

---

## 2. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Results persistence | Re-scan on every page load | No infrastructure; Vercel serverless cache is ephemeral |
| Loading UX | SSE streaming (real progress) | Each block streams as it resolves; better than decorative animation |
| SSE mechanism | `fetch` + `ReadableStream` (Approach 1) | Single API route; works for POST; no EventSource limitations |
| Backend | Next.js API routes only | All checks are HTTP/HTML; no Python changes needed |
| Browser block | Playwright service skeleton | Separate Express app; mock response now; real Playwright in V1 |

---

## 3. Architecture & Data Flow

```
/agent-report (landing)
    │ user submits URL
    ▼
Navigate to /agent-report/[domain]
    │
    ▼ (on mount — client component)
POST /api/agent-check  { url }
    │
    ├─► checkMachineInterface(url)    ─┐
    ├─► callBrowserService(url)        │  Promise.allSettled (parallel)
    ├─► checkAgentDiscovery(url)       │  30s total timeout
    └─► checkAuthSecurity(url)        ─┘
           │
           │  As each Promise settles → SSE event enqueued
           ▼
    ReadableStream (text/event-stream)
           │
    Client reads stream, updates state per event
           │
           ▼
    Final "complete" event → render full ReportLayout
```

### SSE Event Protocol

```typescript
// Emitted as each parallel block resolves:
{ type: "block", block: "machineInterface",   result: BlockResult }
{ type: "block", block: "browserOperability", result: BlockResult }
{ type: "block", block: "agentDiscovery",     result: BlockResult }
{ type: "block", block: "authSecurity",       result: BlockResult }

// After all 4 blocks settle:
{ type: "complete", result: AgentCheckResponse }

// On unrecoverable error during stream (bad URL, timeout):
{ type: "error", message: string }
// Note: rate limit errors return HTTP 429 before the stream opens
```

Each SSE line: `data: <JSON>\n\n`

---

## 4. Scoring System

**Total: 0–100 points across 4 blocks**

| Block | Points | MVP status |
|---|---|---|
| Block 1 — Machine Interface | 30 | Full implementation |
| Block 2 — Browser Operability | 25 | Stub (score: 0, status: "pending") |
| Block 3 — Agent Discovery | 25 | Full implementation |
| Block 4 — Auth & Security | 20 | Full implementation |

### Grades

| Score | Grade | Colour |
|---|---|---|
| 0–25 | Not Agent Ready | `#ef4444` |
| 26–50 | Early Stage | `#f97316` |
| 51–75 | Agent Friendly | `#eab308` |
| 76–90 | Agent Ready | `#22c55e` |
| 91–100 | Agent Native | `#3b82f6` |

---

## 5. Check Modules

### Block 1 — Machine Interface (30 pts)

**1.1 MCP Server Detection (10 pts)**
- Sequential GET: `/.well-known/mcp.json` → `/.well-known/ai-plugin.json` → `https://mcp.so/api/search?q={domain}`
- Any hit → 10 pts; none → 0 pts
- Stores: `found: boolean`, `url?: string`

**1.2 OpenAPI / Swagger Specification (8 pts)**
- Parallel GET on 7 paths: `/openapi.json`, `/swagger.json`, `/api-docs`, `/api/openapi.json`, `/api/v1/openapi.json`, `/docs/api.json`, `/api/swagger.json`
- Valid JSON with `paths` or `openapi` field → 8 pts; JSON found but minimal → 4 pts; not found → 0 pts
- Stores: `found: boolean`, `url?: string`, `spec?: object`

**1.3 API Description Coverage (6 pts)**
- Only if OpenAPI found. Count `paths[*][method]` entries with non-empty `description` or `summary`.
- >70% → 6 pts; 40–70% → 4 pts; 10–40% → 2 pts; <10% → 0 pts
- Stores: `percentage: number | null`

**1.4 Public API Exists (6 pts)**
- Parse homepage HTML for: links containing `/developers`, `/api`, `/docs`; nav text "API", "Developers", "Documentation"; `<link rel="api">`; `/api/` in robots.txt
- 2+ signals → 6 pts; 1 signal → 3 pts; none → 0 pts

---

### Block 2 — Browser Operability (25 pts) — STUB

Returns `{ score: 0, maxScore: 25, status: "pending", checks: { semanticHtml, ariaAttributes, stableUrls, keyboardNavigation, noCaptcha } }` with all checks at score 0.

Called via `callBrowserService(url)` which reads `PLAYWRIGHT_SERVICE_URL` env var. If unset or call fails, returns mock gracefully.

```typescript
// TODO: implement with Playwright service in V1.0
interface BrowserOperabilityCheck {
  semanticHtml:       CheckResult  // 7 pts
  ariaAttributes:     CheckResult  // 5 pts
  stableUrls:         CheckResult  // 5 pts
  keyboardNavigation: CheckResult  // 4 pts
  noCaptcha:          CheckResult  // 4 pts
}
```

---

### Block 3 — Agent Discovery (25 pts)

**3.1 llms.txt Quality (8 pts)**
- GET `/llms.txt`; not found → 0 pts
- If found: file present → +2; has `- ` link lines → +1; has `## API`/`## Tools`/`## Actions`/`## Capabilities`/`## Integrations` sections → +3; word count ≥ 200 → +2
- Stores: `found: boolean`, `hasActionSections: boolean`, `wordCount: number`

**3.2 Robots.txt AI Permissions (6 pts)**
- Parse `/robots.txt` for: `anthropic-ai`, `gpt-bot`, `claude-bot`, `perplexity-bot`, `cohere-ai`, `google-extended`, `amazonbot`
- Un-mentioned = allowed; `Disallow: /` = blocked; wildcard `*` with `Disallow: /` = all blocked unless individually excepted
- All 7 allowed → 6 pts; ≥5 allowed (1–2 blocked) → 4 pts; 3–4 blocked → 2 pts; ≥5 blocked → 0 pts
- Stores: `allowedBots: string[]`, `blockedBots: string[]`

**3.3 Schema.org Markup (6 pts)**
- Parse `<script type="application/ld+json">` on homepage
- High value (2 pts each, max 6): `WebAPI`, `APIReference`, `SoftwareApplication`, `Action`, `EntryPoint`
- Medium value (1 pt each): `Service`, `Organization`, `WebSite`, `Product`
- Stores: `typesFound: string[]`

**3.4 SDK Documentation (5 pts)**
- Scan homepage + `/developers` + `/docs` HTML
- Links to `npmjs.com` → +2; links to `pypi.org` → +2; GitHub link + "SDK" text → +1; `npm install`/`pip install` in code blocks → +2; "SDK" in nav/headings → +1
- 5+ signals → 5 pts; 3–4 → 3 pts; 1–2 → 1 pt; 0 → 0 pts

---

### Block 4 — Auth & Security (20 pts)

**4.1 OAuth 2.0 Support (8 pts)**
- GET `/.well-known/oauth-authorization-server` + `/.well-known/openid-configuration`
- Well-known endpoint found → 8 pts; text mention in `/developers`/`/docs` HTML → 4 pts; none → 0 pts
- Stores: `found: boolean`, `method: "well-known" | "docs" | null`

**4.2 API Key / Token Support (6 pts)**
- GET `/settings`, `/settings/api`, `/account`, `/account/api`, `/developers`, `/api-keys`
- HTML contains "API key", "API token", "Access token", "Personal access token" → score by specificity
- Dedicated API key management page found → 6 pts; mentioned in docs → 3 pts; none → 0 pts

**4.3 CORS Policy (6 pts)**
- If API endpoint found in Block 1: OPTIONS request, inspect `Access-Control-Allow-Origin`
- `*` → 6 pts; specific domain → 3 pts; header absent → 1 pt; no API found → 0 pts, `status: "no_api_found"`
- Stores: `policy: string | null`

---

## 6. API Route

**`POST /api/agent-check`**

```
Headers:  Content-Type: application/json
Body:     { url: string }
Response: Content-Type: text/event-stream
          Transfer-Encoding: chunked
```

Implementation steps:
1. Validate + normalise URL → `{ url: string, domain: string }`. Add `https://` if no scheme. Strip path, extract domain.
2. Rate limit: max 10 scans/IP/hour. In-memory `Map<ip, number[]>` (timestamps). If exceeded, return HTTP 429 JSON `{ error: "Rate limit exceeded" }` before opening any stream.
3. Create `ReadableStream` with `start(controller)`.
4. Inside `start`: kick off `Promise.allSettled([checkMachineInterface, callBrowserService, checkAgentDiscovery, checkAuthSecurity])` wrapped in a 30s `Promise.race` timeout.
5. Use `.then()` on each individual promise to enqueue its block event immediately on resolution (not waiting for all 4).
6. After all settle: compute total score + grade, enqueue `complete` event, close controller.
7. User-Agent for all outbound requests: `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL}/agent-report)`

**Utility functions (`lib/agent-check/utils.ts`):**
```typescript
fetchWithTimeout(url, options?, timeoutMs = 8000): Promise<Response>
normalizeUrl(input: string): { url: string; domain: string }
checkRateLimit(ip: string): boolean
```

---

## 7. TypeScript Types (`lib/agent-check/types.ts`)

```typescript
interface AgentCheckResponse {
  domain: string
  scannedAt: string            // ISO 8601
  totalScore: number
  grade: string
  gradeColor: string           // hex
  blocks: {
    machineInterface:    BlockResult
    browserOperability:  BlockResult & { status: "pending" | "complete" }
    agentDiscovery:      BlockResult
    authSecurity:        BlockResult
  }
}

interface BlockResult {
  score: number
  maxScore: number
  checks: Record<string, CheckResult>
}

interface CheckResult {
  score: number
  maxScore: number
  found?: boolean
  url?: string
  evidence?: string
  // block-specific fields via intersection types in each module
}

type SSEEvent =
  | { type: "block"; block: keyof AgentCheckResponse["blocks"]; result: BlockResult }
  | { type: "complete"; result: AgentCheckResponse }
  | { type: "error"; message: string }
```

No `any`. All block-specific fields (e.g. `allowedBots`, `percentage`, `policy`) added via intersection types inside each module file.

---

## 8. UI Pages & Components

### Pages

**`/app/agent-report/page.tsx`** — server component with `"use client"` form child (`AgentReportForm`). Layout: `max-w-3xl mx-auto`, same visual language as existing `HomePage`. On submit: normalise URL, extract domain, `router.push('/agent-report/${domain}')`.

**`/app/agent-report/[domain]/page.tsx`** — `"use client"`. Reads `params.domain`. On mount, POSTs to `/api/agent-check` and reads `ReadableStream`. State: `idle | scanning | complete | error`. Renders `<ScanProgress>` during scan (updates per block event), `<ReportLayout>` on complete.

**`/app/agent-report/[domain]/loading.tsx`** — static skeleton: 4 grey placeholder cards shown during Next.js hydration.

### Components (`/components/agent-report/`)

| Component | Responsibility |
|---|---|
| `ScanProgress` | Animated step list; each step activates on its block SSE event |
| `ScoreHero` | Large score number + grade badge + scan date |
| `BlockCard` | Score fraction + progress bar; "Coming soon" variant for Block 2 |
| `CheckItem` | Row: ✓/~/✗ icon + name + `score/max` + evidence string |
| `BlockDetail` | Accordion section containing `<CheckItem>` list |
| `PendingBlock` | Block 2 placeholder with "Browser scan — coming soon" |
| `ReportLayout` | Hero + 4 BlockCards + 4 BlockDetails + share footer |

**Grade colours** applied via `style={{ color }}` (dynamic hex, not Tailwind class).

**Check icons:** ✓ green (full score), ~ yellow (partial), ✗ red (zero).

**Share footer:** "Share this report" copies current URL to clipboard; "Scan another site" links to `/agent-report`; "Check AI visibility →" links to `/`.

---

## 9. Playwright Service Skeleton

**Location:** `/playwright-service/` (project root sibling to `/frontend`, `/backend`)

```
playwright-service/
  src/
    index.ts      ← Express server, POST /scan
    types.ts      ← BrowserOperabilityResult
  package.json
  tsconfig.json
  Dockerfile      ← node:20-slim, port 3001
  README.md
  .env.example    ← PORT=3001
```

`POST /scan` accepts `{ url: string }`, returns mock `BrowserOperabilityResult` with all checks at score 0, `status: "complete"` (mock complete, not pending — the pending status is for the frontend block card, not this service response).

**`docker-compose.yml`** additions:
- New `playwright` service: build from `/playwright-service`, port `3001:3001`
- `frontend` service: add `PLAYWRIGHT_SERVICE_URL=http://playwright:3001`

**`frontend/.env.example`** additions:
```
PLAYWRIGHT_SERVICE_URL=   # http://playwright:3001 in docker, leave blank for mock
NEXT_PUBLIC_SITE_URL=     # used in AgentReadinessBot User-Agent header
```

---

## 10. File Structure

```
frontend/
  app/
    agent-report/
      page.tsx                      ← landing + form
      [domain]/
        page.tsx                    ← results page (client, SSE consumer)
        loading.tsx                 ← static skeleton
  app/api/
    agent-check/
      route.ts                      ← POST, SSE orchestrator
  lib/
    agent-check/
      types.ts                      ← all TS types
      utils.ts                      ← fetchWithTimeout, normalizeUrl, rateLimit
      machine-interface.ts          ← Block 1
      browser-operability.ts        ← Block 2 stub + full types
      agent-discovery.ts            ← Block 3
      auth-security.ts              ← Block 4
      scoring.ts                    ← grade/color from score
      index.ts                      ← orchestrator (runs 4 blocks)
  components/
    agent-report/
      ScanProgress.tsx
      ScoreHero.tsx
      BlockCard.tsx
      CheckItem.tsx
      BlockDetail.tsx
      PendingBlock.tsx
      ReportLayout.tsx

playwright-service/
  src/
    index.ts
    types.ts
  package.json
  tsconfig.json
  Dockerfile
  README.md
  .env.example
```

---

## 11. Constraints & Non-Goals

- No Python backend changes
- No database — results not persisted; every page load re-scans
- No Vercel KV in MVP — in-memory rate limit only (resets on cold start)
- No headless browser in MVP — Block 2 is always score 0 / pending
- No LLM calls in MVP — all checks are deterministic HTTP/HTML parsing
- No `any` TypeScript
- Vercel serverless timeout: 30s total scan, 8s per individual check
- Expected real-world score range for top SaaS: 40–80 / 100
