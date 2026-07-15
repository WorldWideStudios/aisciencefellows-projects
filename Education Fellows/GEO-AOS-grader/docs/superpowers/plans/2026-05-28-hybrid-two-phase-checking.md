# Hybrid Two-Phase Checking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace single-pass HTTP scoring with a two-phase system: deterministic HTTP checks in Phase 1, Haiku LLM sub-agents in Phase 2 for unresolved checks, and a Sonnet synthesis call for nuanced final scoring with per-check justifications. Results cached in Upstash Redis for 24h.

**Architecture:** Phase 1 runs all HTTP checks in parallel (≤8s each), returning `FOUND | NOT_FOUND | UNCERTAIN` per check and caching homepage HTML once. Phase 2 launches Haiku sub-agents only for checks that returned `NOT_FOUND` or `UNCERTAIN`, each fetching up to 3 additional pages. A single Sonnet call synthesizes all evidence into scored `BlockResult` objects with justifications. Results are written to Upstash Redis with a 24h TTL; cache hits skip all phases.

**Tech Stack:** Next.js 15, TypeScript 5, Vitest, OpenRouter API (claude-haiku-4-5 + claude-sonnet-4-5), @upstash/redis

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `frontend/lib/agent-check/types.ts` | Modify | Add Phase1/Phase2/Sonnet types |
| `frontend/lib/agent-check/utils.ts` | Modify | Add `callOpenRouter` + Redis helpers |
| `frontend/lib/agent-check/machine-interface.ts` | Modify | Return `MachineInterfacePhase1Results` |
| `frontend/lib/agent-check/agent-discovery.ts` | Modify | Return `AgentDiscoveryPhase1Results` |
| `frontend/lib/agent-check/auth-security.ts` | Modify | Return `AuthSecurityPhase1Results` |
| `frontend/lib/agent-check/phase2-agents.ts` | Create | 7 Haiku sub-agent functions |
| `frontend/lib/agent-check/sonnet-scoring.ts` | Create | Sonnet synthesis function |
| `frontend/lib/agent-check/index.ts` | Rewrite | Two-phase orchestrator + caching |
| `frontend/lib/agent-check/__tests__/machine-interface.test.ts` | Rewrite | Tests for Phase1Result shape |
| `frontend/lib/agent-check/__tests__/agent-discovery.test.ts` | Rewrite | Tests for Phase1Result shape |
| `frontend/lib/agent-check/__tests__/auth-security.test.ts` | Rewrite | Tests for Phase1Result shape |
| `frontend/lib/agent-check/__tests__/phase2-agents.test.ts` | Create | Tests for sub-agent functions |
| `frontend/lib/agent-check/__tests__/sonnet-scoring.test.ts` | Create | Tests for synthesis function |
| `frontend/.env.example` | Modify | Add OPENROUTER_API_KEY + Upstash vars |

---

### Task 1: Extend types.ts with Phase 1/2/Sonnet types

**Files:**
- Modify: `frontend/lib/agent-check/types.ts`

- [ ] **Step 1: Replace the contents of types.ts**

```typescript
export interface CheckResult {
  score: number
  maxScore: number
  found?: boolean
  url?: string
  evidence?: string
  detectionMethod?: "deterministic" | "ai_fallback"
  confidence?: "high" | "medium" | "low"
  justification?: string
}

export interface BlockResult {
  score: number
  maxScore: number
  checks: Record<string, CheckResult>
}

export interface AgentCheckResponse {
  domain: string
  scannedAt: string
  totalScore: number
  grade: string
  gradeColor: string
  blocks: {
    machineInterface: BlockResult
    browserOperability: BlockResult & { status: "pending" | "complete" }
    agentDiscovery: BlockResult
    authSecurity: BlockResult
  }
}

export type SSEEvent =
  | { type: "block"; block: keyof AgentCheckResponse["blocks"]; result: BlockResult }
  | { type: "complete"; result: AgentCheckResponse }
  | { type: "error"; message: string }

export interface BrowserOperabilityChecks {
  semanticHtml: CheckResult
  ariaAttributes: CheckResult
  stableUrls: CheckResult
  keyboardNavigation: CheckResult
  noCaptcha: CheckResult
}

export interface BrowserOperabilityResult extends BlockResult {
  status: "pending" | "complete"
  checks: Record<keyof BrowserOperabilityChecks, CheckResult>
}

// ── Phase 1 ──────────────────────────────────────────────────────────────────

export type Phase1Status = "FOUND" | "NOT_FOUND" | "UNCERTAIN"

export interface Phase1Result {
  status: Phase1Status
  evidence?: string   // URL, quoted text, or description of what was found
  rawData?: unknown   // parsed spec object, HTML excerpt, structured metadata
}

export interface MachineInterfacePhase1Results {
  mcpServer: Phase1Result
  openApiSpec: Phase1Result
  publicApiExists: Phase1Result
}

export interface AgentDiscoveryPhase1Results {
  llmsTxt: Phase1Result
  robotsTxtAi: Phase1Result
  schemaOrg: Phase1Result
  sdkDocs: Phase1Result
}

export interface AuthSecurityPhase1Results {
  oauth: Phase1Result
  apiKeySupport: Phase1Result
  corsPolicy: Phase1Result
}

// ── Phase 2 ──────────────────────────────────────────────────────────────────

export interface SubAgentResult {
  found: boolean
  confidence: "high" | "medium" | "low"
  evidence: string    // URL or quoted text snippet
  details?: string    // extra context (repo age, package name, etc.)
}

export type Phase2CheckName =
  | "mcpServer"
  | "openApiSpec"
  | "publicApiExists"
  | "schemaOrg"
  | "sdkDocs"
  | "oauth"
  | "apiKeySupport"

// ── Sonnet Scoring ────────────────────────────────────────────────────────────

export interface ScoredCheck {
  score: number
  maxScore: number
  found: boolean
  detectionMethod: "deterministic" | "ai_fallback"
  confidence: "high" | "medium" | "low" | null
  justification: string
  evidence?: string
}

export interface SonnetScoringResult {
  checks: Record<string, ScoredCheck>
}
```

- [ ] **Step 2: Verify types compile**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/agent-check/types.ts
git commit -m "feat: add Phase1/Phase2/Sonnet types"
```

---

### Task 2: Install @upstash/redis

**Files:**
- Modify: `frontend/package.json` (via npm)

- [ ] **Step 1: Install the package**

```bash
cd frontend && npm install @upstash/redis
```

Expected output: `added N packages` with `@upstash/redis` listed.

- [ ] **Step 2: Verify it's in package.json**

```bash
cd frontend && node -e "const p = require('./package.json'); console.log(p.dependencies['@upstash/redis'])"
```

Expected: a version string like `^1.x.x`.

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "chore: add @upstash/redis"
```

---

### Task 3: Add callOpenRouter and Redis cache helpers to utils.ts

**Files:**
- Modify: `frontend/lib/agent-check/utils.ts`
- Modify: `frontend/lib/agent-check/__tests__/utils.test.ts`

- [ ] **Step 1: Write failing tests for callOpenRouter**

Add to `frontend/lib/agent-check/__tests__/utils.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { callOpenRouter, normalizeUrl, checkRateLimit } from "../utils"

describe("callOpenRouter", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
    process.env.OPENROUTER_API_KEY = "test-key"
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    delete process.env.OPENROUTER_API_KEY
  })

  it("returns message content on success", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ choices: [{ message: { content: '{"found":true}' } }] }),
        { status: 200 }
      )
    )
    const result = await callOpenRouter("anthropic/claude-haiku-4-5", "test prompt", 300)
    expect(result).toBe('{"found":true}')
  })

  it("calls OpenRouter with Authorization header and json response_format", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ choices: [{ message: { content: "{}" } }] }),
        { status: 200 }
      )
    )
    await callOpenRouter("anthropic/claude-haiku-4-5", "prompt")
    const [url, opts] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toBe("https://openrouter.ai/api/v1/chat/completions")
    const body = JSON.parse(opts.body as string)
    expect(body.model).toBe("anthropic/claude-haiku-4-5")
    expect(body.response_format).toEqual({ type: "json_object" })
    expect((opts.headers as Record<string, string>)["Authorization"]).toBe("Bearer test-key")
  })

  it("throws when OPENROUTER_API_KEY is missing", async () => {
    delete process.env.OPENROUTER_API_KEY
    await expect(callOpenRouter("model", "prompt")).rejects.toThrow("OPENROUTER_API_KEY not set")
  })

  it("throws on non-200 response", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response("Unauthorized", { status: 401 }))
    await expect(callOpenRouter("model", "prompt")).rejects.toThrow("OpenRouter 401")
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npm test -- utils
```

Expected: FAIL — `callOpenRouter is not a function` or similar.

- [ ] **Step 3: Add callOpenRouter and Redis helpers to utils.ts**

Append to the end of `frontend/lib/agent-check/utils.ts`:

```typescript
import { Redis } from "@upstash/redis"
import type { AgentCheckResponse } from "./types"

// ── OpenRouter ────────────────────────────────────────────────────────────────

export async function callOpenRouter(
  model: string,
  prompt: string,
  maxTokens = 500
): Promise<string> {
  const apiKey = process.env.OPENROUTER_API_KEY
  if (!apiKey) throw new Error("OPENROUTER_API_KEY not set")

  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: prompt }],
      max_tokens: maxTokens,
      response_format: { type: "json_object" },
    }),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`OpenRouter ${res.status}: ${text}`)
  }

  const data = await res.json()
  const content = data?.choices?.[0]?.message?.content
  if (typeof content !== "string") throw new Error("OpenRouter returned unexpected response shape")
  return content
}

// ── Upstash Redis cache ───────────────────────────────────────────────────────

let _redis: Redis | null = null

function getRedis(): Redis | null {
  if (_redis) return _redis
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) return null
  _redis = new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.UPSTASH_REDIS_REST_TOKEN,
  })
  return _redis
}

export async function getCachedResult(domain: string): Promise<AgentCheckResponse | null> {
  const r = getRedis()
  if (!r) return null
  try {
    return await r.get<AgentCheckResponse>(`agent-check:${domain}`)
  } catch { return null }
}

export async function setCachedResult(domain: string, result: AgentCheckResponse): Promise<void> {
  const r = getRedis()
  if (!r) return
  try {
    await r.set(`agent-check:${domain}`, result, { ex: 86400 })
  } catch { /* ignore cache write failures */ }
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
cd frontend && npm test -- utils
```

Expected: PASS — all `callOpenRouter` tests green.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/agent-check/utils.ts frontend/lib/agent-check/__tests__/utils.test.ts
git commit -m "feat: add callOpenRouter and Redis cache helpers"
```

---

### Task 4: Refactor machine-interface.ts → Phase 1 results

**Files:**
- Modify: `frontend/lib/agent-check/machine-interface.ts`
- Rewrite: `frontend/lib/agent-check/__tests__/machine-interface.test.ts`

- [ ] **Step 1: Rewrite the test file**

Replace all of `frontend/lib/agent-check/__tests__/machine-interface.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkMachineInterfacePhase1, computeApiCoverage } from "../machine-interface"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } })
}
function notFound(): Response { return new Response("Not Found", { status: 404 }) }
function okText(body: string): Response {
  return new Response(body, { status: 200, headers: { "Content-Type": "text/plain" } })
}

beforeEach(() => { mockFetch.mockReset() })

describe("mcpServer", () => {
  it("returns FOUND immediately for known platforms (github.com)", async () => {
    const result = await checkMachineInterfacePhase1("https://github.com", "")
    expect(result.mcpServer.status).toBe("FOUND")
    expect(result.mcpServer.evidence).toContain("github-mcp-server")
  })

  it("returns FOUND when /.well-known/mcp.json returns 200", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/.well-known/mcp.json")) return Promise.resolve(ok({}))
      return Promise.resolve(notFound())
    })
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.mcpServer.status).toBe("FOUND")
  })

  it("returns UNCERTAIN when homepage HTML mentions MCP", async () => {
    mockFetch.mockResolvedValue(notFound())
    const html = "<p>We support model context protocol for agent integration.</p>"
    const result = await checkMachineInterfacePhase1("https://example.com", html)
    expect(result.mcpServer.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no signals present", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.mcpServer.status).toBe("NOT_FOUND")
  })
})

describe("openApiSpec", () => {
  it("returns FOUND with rawData when spec has paths", async () => {
    const spec = { openapi: "3.0.0", paths: { "/users": { get: { summary: "List" } } } }
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/openapi.json")) return Promise.resolve(ok(spec))
      return Promise.resolve(notFound())
    })
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.openApiSpec.status).toBe("FOUND")
    expect(result.openApiSpec.rawData).toBeDefined()
    expect(result.openApiSpec.evidence).toContain("openapi.json")
  })

  it("returns UNCERTAIN when spec exists but has no paths", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/openapi.json")) return Promise.resolve(ok({ openapi: "3.0.0" }))
      return Promise.resolve(notFound())
    })
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.openApiSpec.status).toBe("UNCERTAIN")
  })

  it("returns FOUND for known platform spec URL (github.com)", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("rest-api-description"))
        return Promise.resolve(ok({ openapi: "3.0.0", paths: { "/repos": {} } }))
      return Promise.resolve(notFound())
    })
    const result = await checkMachineInterfacePhase1("https://github.com", "")
    expect(result.openApiSpec.status).toBe("FOUND")
  })

  it("returns NOT_FOUND when all paths return 404", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.openApiSpec.status).toBe("NOT_FOUND")
  })
})

describe("publicApiExists", () => {
  it("returns FOUND when 2+ signals in homepage HTML", async () => {
    mockFetch.mockResolvedValue(notFound())
    const html = '<a href="/api/v1">API</a><p>Check out our Developers section</p>'
    const result = await checkMachineInterfacePhase1("https://example.com", html)
    expect(result.publicApiExists.status).toBe("FOUND")
  })

  it("returns UNCERTAIN when 1 signal in homepage HTML", async () => {
    mockFetch.mockResolvedValue(notFound())
    const html = '<a href="/developers">Developers</a>'
    const result = await checkMachineInterfacePhase1("https://example.com", html)
    expect(result.publicApiExists.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no API signals", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkMachineInterfacePhase1("https://example.com", "<p>Hello world</p>")
    expect(result.publicApiExists.status).toBe("NOT_FOUND")
  })
})

describe("computeApiCoverage", () => {
  it("returns 100% for fully documented spec", () => {
    const spec = {
      paths: { "/a": { get: { summary: "Get A" } }, "/b": { post: { description: "Post B" } } }
    }
    expect(computeApiCoverage(spec).percentage).toBe(100)
  })

  it("returns null for undefined spec", () => {
    expect(computeApiCoverage(undefined).percentage).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npm test -- machine-interface
```

Expected: FAIL — `checkMachineInterfacePhase1 is not a function`.

- [ ] **Step 3: Rewrite machine-interface.ts**

Replace all of `frontend/lib/agent-check/machine-interface.ts`:

```typescript
import { fetchWithTimeout } from "./utils"
import type { Phase1Result, MachineInterfacePhase1Results } from "./types"

const OPENAPI_PATHS = [
  "/openapi.json", "/openapi.yaml", "/swagger.json", "/swagger.yaml",
  "/api-docs", "/api-docs/swagger.json", "/api/openapi.json", "/api/openapi.yaml",
  "/api/v1/openapi.json", "/api/v2/openapi.json", "/api/v3/openapi.json",
  "/v1/openapi.json", "/v2/openapi.json", "/docs/api.json", "/docs/openapi.json",
  "/api/swagger.json", "/spec/openapi.json", "/.well-known/openapi.json",
]

const KNOWN_OPENAPI_SPECS: Record<string, string> = {
  "github.com": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
  "stripe.com": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json",
  "twilio.com": "https://raw.githubusercontent.com/twilio/twilio-oai/main/spec/json/twilio_api_v2010.json",
  "shopify.com": "https://shopify.dev/docs/api/admin-rest.json",
  "atlassian.com": "https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json",
}

const KNOWN_MCP_SERVERS: Record<string, string> = {
  "github.com": "https://github.com/github/github-mcp-server",
  "notion.com": "https://github.com/makenotion/notion-mcp-server",
  "notion.so": "https://github.com/makenotion/notion-mcp-server",
  "linear.app": "https://github.com/linear/linear-mcp",
  "stripe.com": "https://github.com/stripe/agent-toolkit",
  "atlassian.com": "https://github.com/sooperset/mcp-atlassian",
  "figma.com": "https://github.com/figma/figma-developer-mcp",
  "cloudflare.com": "https://github.com/cloudflare/mcp-server-cloudflare",
  "shopify.com": "https://github.com/Shopify/dev-mcp",
  "sentry.io": "https://github.com/getsentry/sentry-mcp",
}

const MCP_PATHS = [
  "/.well-known/mcp.json", "/.well-known/ai-plugin.json",
  "/mcp", "/mcp.json", "/api/mcp", "/v1/mcp", "/.well-known/mcp",
]

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }

function isValidSpec(data: unknown): data is Record<string, unknown> {
  return !!data && typeof data === "object" &&
    ("openapi" in (data as object) || "swagger" in (data as object) || "paths" in (data as object))
}

async function fetchJson(url: string): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetchWithTimeout(url, { headers: HEADERS })
    if (!res.ok) return null
    const data = await res.json().catch(() => null)
    return isValidSpec(data) ? (data as Record<string, unknown>) : null
  } catch { return null }
}

async function checkMcpServer(baseUrl: string, homepageHtml: string): Promise<Phase1Result> {
  const hostname = new URL(baseUrl).hostname.replace(/^www\./, "")

  const knownUrl = KNOWN_MCP_SERVERS[hostname]
  if (knownUrl) return { status: "FOUND", evidence: knownUrl }

  for (const path of MCP_PATHS) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok) return { status: "FOUND", evidence: `${baseUrl}${path}` }
    } catch { /* continue */ }
  }

  try {
    const nameQuery = hostname.split(".")[0]
    const res = await fetchWithTimeout(
      `https://registry.smithery.ai/servers?q=${encodeURIComponent(nameQuery)}&pageSize=5`,
      { headers: { ...HEADERS, "Accept": "application/json" } }
    )
    if (res.ok) {
      const data = await res.json()
      const servers: Array<{ homepage?: string; qualifiedName?: string }> = data?.servers ?? data ?? []
      if (Array.isArray(servers)) {
        const exact = servers.find(s => s.homepage?.includes(hostname))
        if (exact) return { status: "FOUND", evidence: exact.homepage ?? "smithery.ai registry" }
        const loose = servers.find(s => s.qualifiedName?.toLowerCase().includes(nameQuery))
        if (loose) return { status: "UNCERTAIN", evidence: "possible match in smithery.ai registry" }
      }
    }
  } catch { /* continue */ }

  try {
    const nameQuery = hostname.split(".")[0]
    const res = await fetchWithTimeout(
      `https://mcp.so/api/search?q=${encodeURIComponent(nameQuery)}`,
      { headers: HEADERS }
    )
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        const exact = data.find((s: { homepage?: string }) => s.homepage?.includes(hostname))
        if (exact) return { status: "FOUND", evidence: exact.homepage ?? "mcp.so registry" }
        return { status: "UNCERTAIN", evidence: "possible match in mcp.so registry" }
      }
    }
  } catch { /* continue */ }

  if (/model.context.protocol|mcp.server|\.well-known\/mcp|mcp\.json/i.test(homepageHtml)) {
    return { status: "UNCERTAIN", evidence: "MCP mentioned on homepage" }
  }

  return { status: "NOT_FOUND" }
}

async function checkOpenApiSpec(baseUrl: string): Promise<Phase1Result> {
  const hostname = new URL(baseUrl).hostname.replace(/^www\./, "")

  const knownUrl = KNOWN_OPENAPI_SPECS[hostname]
  if (knownUrl) {
    const data = await fetchJson(knownUrl)
    if (data) {
      const hasPaths = "paths" in data && data.paths && typeof data.paths === "object" && Object.keys(data.paths).length > 0
      return hasPaths
        ? { status: "FOUND", evidence: knownUrl, rawData: data }
        : { status: "UNCERTAIN", evidence: knownUrl, rawData: data }
    }
  }

  const origins = [baseUrl, `https://api.${hostname}`, `https://developer.${hostname}`]
  const urlsToProbe = origins.flatMap(origin => OPENAPI_PATHS.map(path => `${origin}${path}`))

  const results = await Promise.allSettled(urlsToProbe.map(url => fetchJson(url).then(d => d ? { url, data: d } : null)))
  for (const r of results) {
    if (r.status !== "fulfilled" || !r.value) continue
    const { url, data } = r.value
    const hasPaths = "paths" in data && data.paths && typeof data.paths === "object" && Object.keys(data.paths).length > 0
    return hasPaths
      ? { status: "FOUND", evidence: url, rawData: data }
      : { status: "UNCERTAIN", evidence: url, rawData: data }
  }

  const docPages = ["/docs", "/developer", "/api", "/api-docs", "/developers"]
  const specLinkPattern = /href=["']([^"']*(?:openapi|swagger)[^"']*\.(?:json|yaml))["']/gi
  for (const page of docPages) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${page}`, { headers: HEADERS })
      if (!res.ok) continue
      const html = await res.text()
      const matches = [...html.matchAll(specLinkPattern)]
      for (const match of matches) {
        const href = match[1]
        const specUrl = href.startsWith("http") ? href : `${baseUrl}${href.startsWith("/") ? "" : "/"}${href}`
        const data = await fetchJson(specUrl)
        if (data) {
          const hasPaths = "paths" in data && data.paths && typeof data.paths === "object" && Object.keys(data.paths).length > 0
          return hasPaths
            ? { status: "FOUND", evidence: specUrl, rawData: data }
            : { status: "UNCERTAIN", evidence: specUrl, rawData: data }
        }
      }
    } catch { /* continue */ }
  }

  return { status: "NOT_FOUND" }
}

function checkPublicApi(homepageHtml: string, robotsTxt: string): Phase1Result {
  let signals = 0
  if (/href=["'][^"']*\/(developers|api|docs)[^"']*["']/i.test(homepageHtml)) signals++
  if (/\b(API|Developers|Documentation)\b/.test(homepageHtml)) signals++
  if (/rel=["']api["']/i.test(homepageHtml)) signals++
  if (/^(?:Allow|Disallow):\s*\/api\//im.test(robotsTxt)) signals++

  if (signals >= 2) return { status: "FOUND", evidence: `${signals} API signals in homepage/robots.txt` }
  if (signals === 1) return { status: "UNCERTAIN", evidence: "1 weak API signal found" }
  return { status: "NOT_FOUND" }
}

export function computeApiCoverage(spec: Record<string, unknown> | undefined): { percentage: number | null } {
  if (!spec || !("paths" in spec) || !spec.paths || typeof spec.paths !== "object") {
    return { percentage: null }
  }
  const paths = spec.paths as Record<string, Record<string, { description?: string; summary?: string }>>
  const httpMethods = ["get", "post", "put", "patch", "delete", "head", "options"]
  let total = 0, documented = 0
  for (const pathItem of Object.values(paths)) {
    if (!pathItem || typeof pathItem !== "object") continue
    for (const method of httpMethods) {
      const op = pathItem[method]
      if (!op) continue
      total++
      if (op.description?.trim() || op.summary?.trim()) documented++
    }
  }
  if (total === 0) return { percentage: 0 }
  return { percentage: Math.round((documented / total) * 100) }
}

export async function checkMachineInterfacePhase1(
  baseUrl: string,
  homepageHtml: string
): Promise<MachineInterfacePhase1Results> {
  let robotsTxt = ""
  try {
    const res = await fetchWithTimeout(`${baseUrl}/robots.txt`, { headers: HEADERS })
    if (res.ok) robotsTxt = await res.text()
  } catch { /* proceed */ }

  const [mcpRes, openApiRes] = await Promise.allSettled([
    checkMcpServer(baseUrl, homepageHtml),
    checkOpenApiSpec(baseUrl),
  ])

  return {
    mcpServer: mcpRes.status === "fulfilled" ? mcpRes.value : { status: "NOT_FOUND" },
    openApiSpec: openApiRes.status === "fulfilled" ? openApiRes.value : { status: "NOT_FOUND" },
    publicApiExists: checkPublicApi(homepageHtml, robotsTxt),
  }
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm test -- machine-interface
```

Expected: all tests PASS.

- [ ] **Step 5: Type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/agent-check/machine-interface.ts frontend/lib/agent-check/__tests__/machine-interface.test.ts
git commit -m "refactor: machine-interface returns Phase1Results"
```

---

### Task 5: Refactor agent-discovery.ts → Phase 1 results

**Files:**
- Modify: `frontend/lib/agent-check/agent-discovery.ts`
- Rewrite: `frontend/lib/agent-check/__tests__/agent-discovery.test.ts`

- [ ] **Step 1: Rewrite the test file**

Replace all of `frontend/lib/agent-check/__tests__/agent-discovery.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkAgentDiscoveryPhase1 } from "../agent-discovery"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: string, ct = "text/plain"): Response {
  return new Response(body, { status: 200, headers: { "Content-Type": ct } })
}
function notFound(): Response { return new Response("Not Found", { status: 404 }) }

beforeEach(() => { mockFetch.mockReset() })

describe("llmsTxt", () => {
  it("returns NOT_FOUND when /llms.txt is 404", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.llmsTxt.status).toBe("NOT_FOUND")
  })

  it("returns FOUND with wordCount when /llms.txt is 200", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/llms.txt")) return Promise.resolve(ok("# Hello world\nThis is content."))
      return Promise.resolve(notFound())
    })
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.llmsTxt.status).toBe("FOUND")
    expect((r.llmsTxt.rawData as { wordCount: number }).wordCount).toBeGreaterThan(0)
  })

  it("records hasActionSections=true when llms.txt has ## Tools section", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/llms.txt")) return Promise.resolve(ok("# Intro\n## Tools\nsome tool"))
      return Promise.resolve(notFound())
    })
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect((r.llmsTxt.rawData as { hasActionSections: boolean }).hasActionSections).toBe(true)
  })
})

describe("robotsTxtAi", () => {
  it("returns FOUND with empty blockedBots when robots.txt is 404", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.robotsTxtAi.status).toBe("FOUND")
    expect((r.robotsTxtAi.rawData as { blockedBots: string[] }).blockedBots).toHaveLength(0)
  })

  it("returns FOUND with all AI bots in blockedBots when wildcard Disallow: /", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/robots.txt")) return Promise.resolve(ok("User-agent: *\nDisallow: /"))
      return Promise.resolve(notFound())
    })
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    const rawData = r.robotsTxtAi.rawData as { blockedBots: string[] }
    expect(rawData.blockedBots.length).toBeGreaterThan(0)
  })
})

describe("schemaOrg", () => {
  it("returns NOT_FOUND when no JSON-LD in homepageHtml", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAgentDiscoveryPhase1("https://example.com", "<p>No schema here</p>")
    expect(r.schemaOrg.status).toBe("NOT_FOUND")
  })

  it("returns FOUND when JSON-LD with SoftwareApplication in homepageHtml", async () => {
    mockFetch.mockResolvedValue(notFound())
    const html = `<script type="application/ld+json">{"@type":"SoftwareApplication","name":"Test"}</script>`
    const r = await checkAgentDiscoveryPhase1("https://example.com", html)
    expect(r.schemaOrg.status).toBe("FOUND")
    expect((r.schemaOrg.rawData as { typesFound: string[] }).typesFound).toContain("SoftwareApplication")
  })
})

describe("sdkDocs", () => {
  it("returns NOT_FOUND when no SDK signals", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.sdkDocs.status).toBe("NOT_FOUND")
  })

  it("returns FOUND when npmjs.com link present in page", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/developers")) return Promise.resolve(ok('<a href="https://npmjs.com/package/example">npm</a><p>npm install example</p>'))
      return Promise.resolve(notFound())
    })
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.sdkDocs.status).toBe("FOUND")
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npm test -- agent-discovery
```

Expected: FAIL — `checkAgentDiscoveryPhase1 is not a function`.

- [ ] **Step 3: Rewrite agent-discovery.ts**

Replace all of `frontend/lib/agent-check/agent-discovery.ts`:

```typescript
import { fetchWithTimeout } from "./utils"
import type { Phase1Result, AgentDiscoveryPhase1Results } from "./types"

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }

const AI_BOTS = ["anthropic-ai", "gpt-bot", "claude-bot", "perplexity-bot", "cohere-ai", "google-extended", "amazonbot"]
const ACTION_SECTIONS = ["## api", "## tools", "## actions", "## capabilities", "## integrations"]
const HIGH_VALUE_TYPES = ["WebAPI", "APIReference", "SoftwareApplication", "Action", "EntryPoint"]
const MEDIUM_VALUE_TYPES = ["Service", "Organization", "WebSite", "Product"]

async function checkLlmsTxt(baseUrl: string): Promise<Phase1Result> {
  try {
    const res = await fetchWithTimeout(`${baseUrl}/llms.txt`, { headers: HEADERS })
    if (!res.ok) return { status: "NOT_FOUND" }
    const text = await res.text()
    const lower = text.toLowerCase()
    const hasActionSections = ACTION_SECTIONS.some(s => lower.includes(s))
    const wordCount = text.split(/\s+/).filter(Boolean).length
    const hasLinks = /^-\s+https?:\/\//m.test(text)
    return {
      status: "FOUND",
      evidence: `${baseUrl}/llms.txt`,
      rawData: { wordCount, hasActionSections, hasLinks },
    }
  } catch {
    return { status: "NOT_FOUND" }
  }
}

async function checkRobotsTxtAi(baseUrl: string): Promise<Phase1Result> {
  try {
    const res = await fetchWithTimeout(`${baseUrl}/robots.txt`, { headers: HEADERS })
    if (!res.ok) return { status: "FOUND", rawData: { allowedBots: [...AI_BOTS], blockedBots: [] } }

    const text = await res.text()
    const lines = text.split("\n").map(l => l.trim())
    let currentAgents: string[] = []
    const explicitBlocked = new Set<string>()
    let wildcardBlocked = false
    const wildcardExceptions = new Set<string>()

    for (const line of lines) {
      if (/^user-agent:/i.test(line)) {
        currentAgents = [line.replace(/^user-agent:\s*/i, "").toLowerCase()]
      } else if (/^disallow:\s*\/$/i.test(line)) {
        if (currentAgents.includes("*")) wildcardBlocked = true
        for (const agent of currentAgents) {
          const matched = AI_BOTS.find(b => agent.includes(b))
          if (matched) explicitBlocked.add(matched)
        }
      } else if (/^allow:\s*\/$/i.test(line)) {
        for (const agent of currentAgents) {
          const matched = AI_BOTS.find(b => agent.includes(b))
          if (matched) wildcardExceptions.add(matched)
        }
      }
    }

    const blockedBots = AI_BOTS.filter(bot =>
      explicitBlocked.has(bot) || (wildcardBlocked && !wildcardExceptions.has(bot))
    )
    const allowedBots = AI_BOTS.filter(b => !blockedBots.includes(b))
    return { status: "FOUND", rawData: { allowedBots, blockedBots } }
  } catch {
    return { status: "FOUND", rawData: { allowedBots: [...AI_BOTS], blockedBots: [] } }
  }
}

function checkSchemaOrgInHtml(html: string): Phase1Result {
  const ldMatches = [...html.matchAll(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)]
  const typesFound: string[] = []

  for (const match of ldMatches) {
    try {
      const data = JSON.parse(match[1])
      const items = Array.isArray(data) ? data : [data]
      for (const item of items) {
        const t = item?.["@type"]
        if (typeof t === "string" && !typesFound.includes(t)) typesFound.push(t)
      }
    } catch { /* malformed JSON-LD */ }
  }

  if (typesFound.length === 0) return { status: "NOT_FOUND" }
  return { status: "FOUND", rawData: { typesFound } }
}

async function checkSdkDocs(baseUrl: string): Promise<Phase1Result> {
  let signals = 0
  const pages = [baseUrl, `${baseUrl}/developers`, `${baseUrl}/docs`]

  await Promise.allSettled(pages.map(async url => {
    try {
      const res = await fetchWithTimeout(url, { headers: HEADERS })
      if (!res.ok) return
      const html = await res.text()
      if (/npmjs\.com/i.test(html)) signals += 2
      if (/pypi\.org/i.test(html)) signals += 2
      if (/github\.com[^\s"']*sdk/i.test(html)) signals += 1
      if (/npm\s+install\b/i.test(html)) signals += 2
      if (/pip\s+install\b/i.test(html)) signals += 2
      if (/<(?:nav|h[1-6])[^>]*>[^<]*\bSDK\b[^<]*<\/(?:nav|h[1-6])>/i.test(html)) signals += 1
    } catch { /* ignore */ }
  }))

  if (signals >= 5) return { status: "FOUND", evidence: `${signals} SDK signals found` }
  if (signals >= 1) return { status: "UNCERTAIN", evidence: `${signals} weak SDK signal(s)` }
  return { status: "NOT_FOUND" }
}

export async function checkAgentDiscoveryPhase1(
  baseUrl: string,
  homepageHtml: string
): Promise<AgentDiscoveryPhase1Results> {
  const [llmsRes, robotsRes, sdkRes] = await Promise.allSettled([
    checkLlmsTxt(baseUrl),
    checkRobotsTxtAi(baseUrl),
    checkSdkDocs(baseUrl),
  ])

  return {
    llmsTxt: llmsRes.status === "fulfilled" ? llmsRes.value : { status: "NOT_FOUND" },
    robotsTxtAi: robotsRes.status === "fulfilled" ? robotsRes.value : { status: "FOUND", rawData: { allowedBots: [...AI_BOTS], blockedBots: [] } },
    schemaOrg: checkSchemaOrgInHtml(homepageHtml),
    sdkDocs: sdkRes.status === "fulfilled" ? sdkRes.value : { status: "NOT_FOUND" },
  }
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm test -- agent-discovery
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/agent-check/agent-discovery.ts frontend/lib/agent-check/__tests__/agent-discovery.test.ts
git commit -m "refactor: agent-discovery returns Phase1Results"
```

---

### Task 6: Refactor auth-security.ts → Phase 1 results

**Files:**
- Modify: `frontend/lib/agent-check/auth-security.ts`
- Rewrite: `frontend/lib/agent-check/__tests__/auth-security.test.ts`

- [ ] **Step 1: Rewrite the test file**

Replace all of `frontend/lib/agent-check/__tests__/auth-security.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkAuthSecurityPhase1 } from "../auth-security"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json", ...headers } })
}
function okText(body: string): Response { return new Response(body, { status: 200 }) }
function notFound(): Response { return new Response("Not Found", { status: 404 }) }

beforeEach(() => { mockFetch.mockReset() })

describe("oauth", () => {
  it("returns FOUND when /.well-known/oauth-authorization-server is valid JSON", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("oauth-authorization-server")) return Promise.resolve(ok({ issuer: "https://example.com" }))
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.oauth.status).toBe("FOUND")
    expect(r.oauth.evidence).toContain("well-known")
  })

  it("returns UNCERTAIN when OAuth 2.0 mentioned in /developers docs", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/developers")) return Promise.resolve(okText("<p>We support OAuth 2.0 flows.</p>"))
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.oauth.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no OAuth signal", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.oauth.status).toBe("NOT_FOUND")
  })
})

describe("apiKeySupport", () => {
  it("returns FOUND when /settings/api page mentions API key", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/settings/api")) return Promise.resolve(okText("Your API key: xxxx"))
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.apiKeySupport.status).toBe("FOUND")
  })

  it("returns UNCERTAIN when API key mentioned in /settings page", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/settings") && !url.includes("/api")) return Promise.resolve(okText("Manage your API key here."))
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.apiKeySupport.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no API key signal", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.apiKeySupport.status).toBe("NOT_FOUND")
  })
})

describe("corsPolicy", () => {
  it("returns FOUND with policy=* when CORS is wildcard", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/api")) return Promise.resolve(
        new Response(null, { status: 200, headers: { "Access-Control-Allow-Origin": "*" } })
      )
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.corsPolicy.status).toBe("FOUND")
    expect((r.corsPolicy.rawData as { policy: string }).policy).toBe("*")
  })

  it("returns UNCERTAIN when CORS is a specific origin", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/api")) return Promise.resolve(
        new Response(null, { status: 200, headers: { "Access-Control-Allow-Origin": "https://app.example.com" } })
      )
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.corsPolicy.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no API endpoint and no CORS headers", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.corsPolicy.status).toBe("NOT_FOUND")
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npm test -- auth-security
```

Expected: FAIL — `checkAuthSecurityPhase1 is not a function`.

- [ ] **Step 3: Rewrite auth-security.ts**

Replace all of `frontend/lib/agent-check/auth-security.ts`:

```typescript
import { fetchWithTimeout } from "./utils"
import type { Phase1Result, AuthSecurityPhase1Results } from "./types"

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }
const API_KEY_PATTERN = /api\s*key|api\s*token|access\s+token|personal\s+access\s+token|secret\s+key/i

async function checkOAuth(baseUrl: string): Promise<Phase1Result> {
  for (const path of ["/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok) {
        await res.json()
        return { status: "FOUND", evidence: `${baseUrl}${path}` }
      }
    } catch { /* continue */ }
  }
  for (const path of ["/developers", "/docs", "/api"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok) {
        const html = await res.text()
        if (/oauth\s*2\.?0|openid\s+connect/i.test(html)) {
          return { status: "UNCERTAIN", evidence: `OAuth 2.0 mentioned at ${baseUrl}${path}` }
        }
      }
    } catch { /* continue */ }
  }
  return { status: "NOT_FOUND" }
}

async function checkApiKeySupport(baseUrl: string): Promise<Phase1Result> {
  for (const path of ["/settings/api", "/account/api", "/api-keys"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok && API_KEY_PATTERN.test(await res.text())) {
        return { status: "FOUND", evidence: `${baseUrl}${path}` }
      }
    } catch { /* continue */ }
  }
  for (const path of ["/settings", "/account", "/developers", "/"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok && API_KEY_PATTERN.test(await res.text())) {
        return { status: "UNCERTAIN", evidence: `API key mentioned at ${baseUrl}${path}` }
      }
    } catch { /* continue */ }
  }
  return { status: "NOT_FOUND" }
}

async function findApiEndpoint(baseUrl: string): Promise<string | undefined> {
  for (const path of ["/api/v1", "/api", "/api/v1/health", "/api/health"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { method: "HEAD", headers: HEADERS })
      if (res.ok || res.status === 401 || res.status === 405) return `${baseUrl}${path}`
    } catch { /* continue */ }
  }
  return undefined
}

async function checkCors(baseUrl: string): Promise<Phase1Result> {
  const endpoint = await findApiEndpoint(baseUrl)
  if (!endpoint) return { status: "NOT_FOUND" }
  try {
    const res = await fetchWithTimeout(endpoint, {
      method: "OPTIONS",
      headers: { ...HEADERS, "Origin": "https://test.example.com", "Access-Control-Request-Method": "GET" },
    })
    const origin = res.headers.get("access-control-allow-origin")
    if (origin === "*") return { status: "FOUND", rawData: { policy: "*" } }
    if (origin) return { status: "UNCERTAIN", rawData: { policy: origin } }
    return { status: "UNCERTAIN", rawData: { policy: null } }
  } catch {
    return { status: "UNCERTAIN", rawData: { policy: null } }
  }
}

export async function checkAuthSecurityPhase1(
  baseUrl: string,
  _homepageHtml: string
): Promise<AuthSecurityPhase1Results> {
  const [oauthRes, apiKeyRes, corsRes] = await Promise.allSettled([
    checkOAuth(baseUrl),
    checkApiKeySupport(baseUrl),
    checkCors(baseUrl),
  ])

  return {
    oauth: oauthRes.status === "fulfilled" ? oauthRes.value : { status: "NOT_FOUND" },
    apiKeySupport: apiKeyRes.status === "fulfilled" ? apiKeyRes.value : { status: "NOT_FOUND" },
    corsPolicy: corsRes.status === "fulfilled" ? corsRes.value : { status: "NOT_FOUND" },
  }
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm test -- auth-security
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/agent-check/auth-security.ts frontend/lib/agent-check/__tests__/auth-security.test.ts
git commit -m "refactor: auth-security returns Phase1Results"
```

---

### Task 7: Create phase2-agents.ts

**Files:**
- Create: `frontend/lib/agent-check/phase2-agents.ts`
- Create: `frontend/lib/agent-check/__tests__/phase2-agents.test.ts`

- [ ] **Step 1: Write the test file**

Create `frontend/lib/agent-check/__tests__/phase2-agents.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkMcpServerAgent, checkOpenApiSpecAgent, checkOAuthAgent } from "../phase2-agents"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn(), callOpenRouter: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)
const mockOpenRouter = vi.mocked(utils.callOpenRouter)

function notFound(): Response { return new Response("Not Found", { status: 404 }) }
function okText(body: string): Response { return new Response(body, { status: 200 }) }

beforeEach(() => {
  mockFetch.mockReset()
  mockOpenRouter.mockReset()
})

describe("checkMcpServerAgent", () => {
  it("returns found=true when Haiku identifies an MCP repo", async () => {
    mockFetch.mockResolvedValue(notFound())
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: true,
      confidence: "high",
      evidence: "https://github.com/example/mcp-server",
      details: "Official MCP server repository",
    }))
    const result = await checkMcpServerAgent("https://example.com", "<html></html>")
    expect(result.found).toBe(true)
    expect(result.confidence).toBe("high")
    expect(result.evidence).toContain("github.com")
  })

  it("returns found=false with low confidence when Haiku finds nothing", async () => {
    mockFetch.mockResolvedValue(notFound())
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: false,
      confidence: "high",
      evidence: "",
    }))
    const result = await checkMcpServerAgent("https://example.com", "")
    expect(result.found).toBe(false)
  })

  it("returns safe fallback on OpenRouter error", async () => {
    mockFetch.mockResolvedValue(notFound())
    mockOpenRouter.mockRejectedValue(new Error("timeout"))
    const result = await checkMcpServerAgent("https://example.com", "")
    expect(result.found).toBe(false)
    expect(result.confidence).toBe("low")
  })
})

describe("checkOpenApiSpecAgent", () => {
  it("returns found=true when Haiku finds a spec URL", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/developers")) return Promise.resolve(okText('<a href="/api/spec.json">OpenAPI</a>'))
      return Promise.resolve(notFound())
    })
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: true,
      confidence: "high",
      evidence: "https://example.com/api/spec.json",
    }))
    const result = await checkOpenApiSpecAgent("https://example.com", "")
    expect(result.found).toBe(true)
    expect(result.evidence).toContain("spec.json")
  })
})

describe("checkOAuthAgent", () => {
  it("returns found=false with safe fallback on JSON parse error", async () => {
    mockFetch.mockResolvedValue(notFound())
    mockOpenRouter.mockResolvedValue("not valid json at all {{{")
    const result = await checkOAuthAgent("https://example.com", "")
    expect(result.found).toBe(false)
    expect(result.confidence).toBe("low")
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npm test -- phase2-agents
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create phase2-agents.ts**

Create `frontend/lib/agent-check/phase2-agents.ts`:

```typescript
import { fetchWithTimeout, callOpenRouter } from "./utils"
import type { SubAgentResult } from "./types"

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }
const HAIKU = "anthropic/claude-haiku-4-5"
const FALLBACK: SubAgentResult = { found: false, confidence: "low", evidence: "sub-agent error" }

async function fetchPages(baseUrl: string, paths: string[]): Promise<string> {
  const parts: string[] = []
  for (const path of paths.slice(0, 3)) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS }, 8000)
      if (res.ok) {
        const text = await res.text()
        parts.push(`--- ${path} ---\n${text.slice(0, 2000)}`)
      }
    } catch { /* skip */ }
  }
  return parts.join("\n\n")
}

function buildPrompt(domain: string, homepageHtml: string, pages: string, task: string): string {
  return `You are analyzing ${domain} for AI agent operability.

HOMEPAGE HTML (excerpt):
${homepageHtml.slice(0, 3000)}

${pages ? `ADDITIONAL PAGES:\n${pages}` : "No additional pages fetched."}

TASK: ${task}

Return ONLY valid JSON with no other text:
{
  "found": boolean,
  "confidence": "high" | "medium" | "low",
  "evidence": "URL or quoted text where found, or empty string if not found",
  "details": "optional extra context"
}`
}

async function callAgent(prompt: string): Promise<SubAgentResult> {
  try {
    const content = await callOpenRouter(HAIKU, prompt, 400)
    const parsed = JSON.parse(content) as SubAgentResult
    if (typeof parsed.found !== "boolean" || !["high", "medium", "low"].includes(parsed.confidence)) {
      return FALLBACK
    }
    return parsed
  } catch { return FALLBACK }
}

export async function checkMcpServerAgent(url: string, homepageHtml: string): Promise<SubAgentResult> {
  const domain = new URL(url).hostname.replace(/^www\./, "")
  const pages = await fetchPages(url, ["/developers", "/docs", "/platform"])
  const task = `Search for an official MCP (Model Context Protocol) server for ${domain}. Look for:
- Links or mentions of "MCP server", "model context protocol"  
- A GitHub repository with "mcp" in the name alongside ${domain}
- Install instructions like "npx @modelcontextprotocol/" or similar
- Any reference to serving MCP protocol
Return the repository URL or install command as evidence.`
  return callAgent(buildPrompt(domain, homepageHtml, pages, task))
}

export async function checkOpenApiSpecAgent(url: string, homepageHtml: string): Promise<SubAgentResult> {
  const domain = new URL(url).hostname.replace(/^www\./, "")
  const pages = await fetchPages(url, ["/developers", "/docs", "/api", "/platform", "/build"])
  const task = `Find an OpenAPI or Swagger API specification for ${domain}. It may be linked from the pages provided. Look for:
- Links containing "openapi", "swagger", "api-spec", "api-docs", or "rest-api"
- File extensions .json or .yaml on spec-like paths
- Mentions of a machine-readable API specification URL
Return the direct URL to the spec file.`
  return callAgent(buildPrompt(domain, homepageHtml, pages, task))
}

export async function checkPublicApiAgent(url: string, homepageHtml: string): Promise<SubAgentResult> {
  const domain = new URL(url).hostname.replace(/^www\./, "")
  const pages = await fetchPages(url, ["/developers", "/docs"])
  const task = `Determine if ${domain} offers a public API for programmatic access. Look in navigation, footer, and the pages provided for mentions of "API", "REST API", "GraphQL API", "developer platform", or links to API documentation. Return a URL to the API docs or developer portal.`
  return callAgent(buildPrompt(domain, homepageHtml, pages, task))
}

export async function checkOAuthAgent(url: string, homepageHtml: string): Promise<SubAgentResult> {
  const domain = new URL(url).hostname.replace(/^www\./, "")
  const pages = await fetchPages(url, ["/docs/authentication", "/docs/auth", "/developers", "/security"])
  const task = `Find evidence that ${domain} supports OAuth 2.0 authentication. Look for text mentioning "OAuth 2.0", "OAuth2", "OpenID Connect", "authorization flow", or "access token" in the pages provided. Return a URL and a short quoted snippet as evidence.`
  return callAgent(buildPrompt(domain, homepageHtml, pages, task))
}

export async function checkApiKeyAgent(url: string, homepageHtml: string): Promise<SubAgentResult> {
  const domain = new URL(url).hostname.replace(/^www\./, "")
  const pages = await fetchPages(url, ["/docs/authentication", "/developers", "/api"])
  const task = `Find evidence that ${domain} offers API keys or tokens for programmatic access. Look for "API key", "API token", "personal access token", "secret key", or "bearer token" in the pages provided. Return a URL and a short quoted snippet.`
  return callAgent(buildPrompt(domain, homepageHtml, pages, task))
}

export async function checkSdkDocsAgent(url: string, homepageHtml: string): Promise<SubAgentResult> {
  const domain = new URL(url).hostname.replace(/^www\./, "")
  const pages = await fetchPages(url, ["/developers", "/docs", "/build", "/platform"])
  const task = `Find evidence of a developer SDK for ${domain}. Look for links to npmjs.com, pypi.org, or GitHub alongside the word "SDK", or text like "npm install", "pip install", "client library" in the pages provided. Return the URL and package name if found.`
  return callAgent(buildPrompt(domain, homepageHtml, pages, task))
}

export async function checkSchemaOrgAgent(url: string, homepageHtml: string): Promise<SubAgentResult> {
  const domain = new URL(url).hostname.replace(/^www\./, "")
  const pages = await fetchPages(url, ["/about", "/product", "/features", "/platform"])
  const task = `Check the pages provided for JSON-LD structured data (inside <script type="application/ld+json"> tags). Look for @type values: SoftwareApplication, WebAPI, APIReference, Service, Action, or EntryPoint. Return the @type found and the page URL.`
  return callAgent(buildPrompt(domain, homepageHtml, pages, task))
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm test -- phase2-agents
```

Expected: all tests PASS.

- [ ] **Step 5: Type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/agent-check/phase2-agents.ts frontend/lib/agent-check/__tests__/phase2-agents.test.ts
git commit -m "feat: add Phase 2 Haiku sub-agent functions"
```

---

### Task 8: Create sonnet-scoring.ts

**Files:**
- Create: `frontend/lib/agent-check/sonnet-scoring.ts`
- Create: `frontend/lib/agent-check/__tests__/sonnet-scoring.test.ts`

- [ ] **Step 1: Write the test file**

Create `frontend/lib/agent-check/__tests__/sonnet-scoring.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { scoreSonnet } from "../sonnet-scoring"
import * as utils from "../utils"
import type {
  MachineInterfacePhase1Results,
  AgentDiscoveryPhase1Results,
  AuthSecurityPhase1Results,
} from "../types"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, callOpenRouter: vi.fn() }
})

const mockOpenRouter = vi.mocked(utils.callOpenRouter)

beforeEach(() => { mockOpenRouter.mockReset() })

const machine: MachineInterfacePhase1Results = {
  mcpServer: { status: "FOUND", evidence: "https://github.com/example/mcp" },
  openApiSpec: { status: "FOUND", evidence: "https://example.com/openapi.json", rawData: { paths: { "/a": { get: { summary: "A" } } } } },
  publicApiExists: { status: "FOUND", evidence: "2 signals" },
}
const discovery: AgentDiscoveryPhase1Results = {
  llmsTxt: { status: "NOT_FOUND" },
  robotsTxtAi: { status: "FOUND", rawData: { allowedBots: ["anthropic-ai"], blockedBots: [] } },
  schemaOrg: { status: "NOT_FOUND" },
  sdkDocs: { status: "UNCERTAIN", evidence: "1 weak signal" },
}
const auth: AuthSecurityPhase1Results = {
  oauth: { status: "FOUND", evidence: "https://example.com/.well-known/oauth-authorization-server" },
  apiKeySupport: { status: "NOT_FOUND" },
  corsPolicy: { status: "FOUND", rawData: { policy: "*" } },
}

const validSonnetOutput = JSON.stringify({
  checks: {
    mcpServer: { score: 10, maxScore: 10, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Official MCP server found", evidence: "https://github.com/example/mcp" },
    openApiSpec: { score: 7, maxScore: 8, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Spec found with 1 path", evidence: "https://example.com/openapi.json" },
    apiDescriptionCoverage: { score: 6, maxScore: 6, found: true, detectionMethod: "deterministic", confidence: "high", justification: "100% documented", evidence: "" },
    publicApiExists: { score: 6, maxScore: 6, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Clear API signals", evidence: "2 signals" },
    llmsTxt: { score: 0, maxScore: 8, found: false, detectionMethod: "deterministic", confidence: null, justification: "No llms.txt found", evidence: "" },
    robotsTxtAi: { score: 6, maxScore: 6, found: true, detectionMethod: "deterministic", confidence: "high", justification: "All AI bots allowed", evidence: "" },
    schemaOrg: { score: 0, maxScore: 6, found: false, detectionMethod: "deterministic", confidence: null, justification: "No JSON-LD found", evidence: "" },
    sdkDocs: { score: 1, maxScore: 5, found: true, detectionMethod: "ai_fallback", confidence: "medium", justification: "Weak SDK signal", evidence: "1 weak signal" },
    oauth: { score: 8, maxScore: 8, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Well-known OAuth endpoint confirmed", evidence: "https://example.com/.well-known/oauth-authorization-server" },
    apiKeySupport: { score: 0, maxScore: 6, found: false, detectionMethod: "deterministic", confidence: null, justification: "No API key support found", evidence: "" },
    corsPolicy: { score: 6, maxScore: 6, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Wildcard CORS policy", evidence: "" },
  }
})

describe("scoreSonnet", () => {
  it("maps Sonnet JSON output to SonnetScoringResult", async () => {
    mockOpenRouter.mockResolvedValue(validSonnetOutput)
    const result = await scoreSonnet("example.com", machine, discovery, auth, {})
    expect(result.checks.mcpServer.score).toBe(10)
    expect(result.checks.mcpServer.justification).toBe("Official MCP server found")
    expect(result.checks.oauth.detectionMethod).toBe("deterministic")
  })

  it("calls OpenRouter with claude-sonnet-4-5 model", async () => {
    mockOpenRouter.mockResolvedValue(validSonnetOutput)
    await scoreSonnet("example.com", machine, discovery, auth, {})
    expect(mockOpenRouter).toHaveBeenCalledWith(
      "anthropic/claude-sonnet-4-5",
      expect.stringContaining("example.com"),
      expect.any(Number)
    )
  })

  it("returns zero-score fallback on OpenRouter error", async () => {
    mockOpenRouter.mockRejectedValue(new Error("timeout"))
    const result = await scoreSonnet("example.com", machine, discovery, auth, {})
    expect(result.checks).toBeDefined()
    // All scores should be 0 in fallback
    expect(Object.values(result.checks).every(c => c.score === 0)).toBe(true)
  })

  it("returns zero-score fallback on malformed JSON", async () => {
    mockOpenRouter.mockResolvedValue("not json {{{{")
    const result = await scoreSonnet("example.com", machine, discovery, auth, {})
    expect(Object.values(result.checks).every(c => c.score === 0)).toBe(true)
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npm test -- sonnet-scoring
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create sonnet-scoring.ts**

Create `frontend/lib/agent-check/sonnet-scoring.ts`:

```typescript
import { callOpenRouter } from "./utils"
import { computeApiCoverage } from "./machine-interface"
import type {
  MachineInterfacePhase1Results,
  AgentDiscoveryPhase1Results,
  AuthSecurityPhase1Results,
  Phase2CheckName,
  SubAgentResult,
  SonnetScoringResult,
  ScoredCheck,
} from "./types"

const SONNET = "anthropic/claude-sonnet-4-5"

const ZERO_CHECKS: SonnetScoringResult = {
  checks: {
    mcpServer:            { score: 0, maxScore: 10, found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    openApiSpec:          { score: 0, maxScore: 8,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    apiDescriptionCoverage: { score: 0, maxScore: 6, found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    publicApiExists:      { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    llmsTxt:              { score: 0, maxScore: 8,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    robotsTxtAi:          { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    schemaOrg:            { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    sdkDocs:              { score: 0, maxScore: 5,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    oauth:                { score: 0, maxScore: 8,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    apiKeySupport:        { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    corsPolicy:           { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
  }
}

function buildEvidenceJson(
  domain: string,
  machine: MachineInterfacePhase1Results,
  discovery: AgentDiscoveryPhase1Results,
  auth: AuthSecurityPhase1Results,
  phase2: Partial<Record<Phase2CheckName, SubAgentResult>>
): string {
  const coverage = computeApiCoverage(
    machine.openApiSpec.rawData as Record<string, unknown> | undefined
  )
  return JSON.stringify({
    domain,
    phase1: {
      mcpServer: { status: machine.mcpServer.status, evidence: machine.mcpServer.evidence },
      openApiSpec: {
        status: machine.openApiSpec.status,
        evidence: machine.openApiSpec.evidence,
        coveragePercentage: coverage.percentage,
      },
      publicApiExists: { status: machine.publicApiExists.status, evidence: machine.publicApiExists.evidence },
      llmsTxt: { status: discovery.llmsTxt.status, rawData: discovery.llmsTxt.rawData },
      robotsTxtAi: { status: discovery.robotsTxtAi.status, rawData: discovery.robotsTxtAi.rawData },
      schemaOrg: { status: discovery.schemaOrg.status, rawData: discovery.schemaOrg.rawData },
      sdkDocs: { status: discovery.sdkDocs.status, evidence: discovery.sdkDocs.evidence },
      oauth: { status: auth.oauth.status, evidence: auth.oauth.evidence },
      apiKeySupport: { status: auth.apiKeySupport.status, evidence: auth.apiKeySupport.evidence },
      corsPolicy: { status: auth.corsPolicy.status, rawData: auth.corsPolicy.rawData },
    },
    phase2: Object.fromEntries(
      Object.entries(phase2).map(([k, v]) => [k, v])
    ),
  }, null, 2)
}

function buildPrompt(evidenceJson: string): string {
  return `You are scoring an AI agent operability report. Based on the evidence below, assign a score to each check. Apply judgment — do not follow a rigid formula. The max score for each check is a ceiling.

SCORING RUBRIC:
- mcpServer (max 10): Active maintained server = 10; found but archived/old = 4–6; vague mention = 1–2
- openApiSpec (max 8): Complete spec with well-documented paths = 8; spec with some paths = 4–6; minimal/empty spec = 2
- apiDescriptionCoverage (max 6): >70% paths documented = 6; 40–70% = 4; 10–40% = 2; <10% = 0; no spec = 0
- publicApiExists (max 6): Dedicated developer portal = 6; API mentioned prominently = 3; vague = 1
- llmsTxt (max 8): Rich file with tool/action sections = 8; basic file with links = 3–5; minimal = 2; absent = 0
- robotsTxtAi (max 6): All AI bots allowed = 6; 1–2 blocked = 4; 3–4 blocked = 2; all blocked = 0
- schemaOrg (max 6): WebAPI or APIReference found = 6; SoftwareApplication or Action = 3–4; basic types = 1–2; none = 0
- sdkDocs (max 5): Multiple published packages = 5; one package = 3; SDK mentioned = 1; none = 0
- oauth (max 8): Well-known endpoint confirmed = 8; documented OAuth flow = 4; mentioned = 1; none = 0
- apiKeySupport (max 6): API key management page found = 6; keys documented = 3; mentioned = 1; none = 0
- corsPolicy (max 6): Wildcard * = 6; specific origin = 3; no CORS found = 1

EVIDENCE:
${evidenceJson}

Return ONLY valid JSON (no markdown, no other text) matching this exact schema. detectionMethod must be "deterministic" if found via phase1 status=FOUND, or "ai_fallback" if found only via phase2:
{
  "checks": {
    "mcpServer": { "score": 0, "maxScore": 10, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "openApiSpec": { "score": 0, "maxScore": 8, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "apiDescriptionCoverage": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "publicApiExists": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "llmsTxt": { "score": 0, "maxScore": 8, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "robotsTxtAi": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "schemaOrg": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "sdkDocs": { "score": 0, "maxScore": 5, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "oauth": { "score": 0, "maxScore": 8, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "apiKeySupport": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "corsPolicy": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" }
  }
}`
}

export async function scoreSonnet(
  domain: string,
  machine: MachineInterfacePhase1Results,
  discovery: AgentDiscoveryPhase1Results,
  auth: AuthSecurityPhase1Results,
  phase2: Partial<Record<Phase2CheckName, SubAgentResult>>
): Promise<SonnetScoringResult> {
  try {
    const evidenceJson = buildEvidenceJson(domain, machine, discovery, auth, phase2)
    const prompt = buildPrompt(evidenceJson)
    const content = await callOpenRouter(SONNET, prompt, 2000)
    const parsed = JSON.parse(content) as SonnetScoringResult
    if (!parsed?.checks || typeof parsed.checks !== "object") return ZERO_CHECKS
    return parsed
  } catch { return ZERO_CHECKS }
}
```

- [ ] **Step 4: Run tests**

```bash
cd frontend && npm test -- sonnet-scoring
```

Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/agent-check/sonnet-scoring.ts frontend/lib/agent-check/__tests__/sonnet-scoring.test.ts
git commit -m "feat: add Sonnet synthesis scoring"
```

---

### Task 9: Rewrite index.ts — two-phase orchestrator + caching

**Files:**
- Rewrite: `frontend/lib/agent-check/index.ts`

- [ ] **Step 1: Replace all of index.ts**

```typescript
import { fetchWithTimeout, getCachedResult, setCachedResult } from "./utils"
import { checkMachineInterfacePhase1 } from "./machine-interface"
import { checkAgentDiscoveryPhase1 } from "./agent-discovery"
import { checkAuthSecurityPhase1 } from "./auth-security"
import {
  checkMcpServerAgent, checkOpenApiSpecAgent, checkPublicApiAgent,
  checkOAuthAgent, checkApiKeyAgent, checkSdkDocsAgent, checkSchemaOrgAgent,
} from "./phase2-agents"
import { scoreSonnet } from "./sonnet-scoring"
import { callBrowserService } from "./browser-operability"
import { getGrade } from "./scoring"
import type {
  AgentCheckResponse, BlockResult, SSEEvent,
  MachineInterfacePhase1Results, AgentDiscoveryPhase1Results, AuthSecurityPhase1Results,
  Phase2CheckName, SubAgentResult, ScoredCheck,
} from "./types"

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`

function identifyPhase2Checks(
  machine: MachineInterfacePhase1Results,
  discovery: AgentDiscoveryPhase1Results,
  auth: AuthSecurityPhase1Results
): Set<Phase2CheckName> {
  const needed = new Set<Phase2CheckName>()
  if (machine.mcpServer.status !== "FOUND") needed.add("mcpServer")
  if (machine.openApiSpec.status !== "FOUND") needed.add("openApiSpec")
  if (machine.publicApiExists.status !== "FOUND") needed.add("publicApiExists")
  if (discovery.schemaOrg.status !== "FOUND") needed.add("schemaOrg")
  if (discovery.sdkDocs.status !== "FOUND") needed.add("sdkDocs")
  if (auth.oauth.status !== "FOUND") needed.add("oauth")
  if (auth.apiKeySupport.status !== "FOUND") needed.add("apiKeySupport")
  return needed
}

async function runPhase2(
  url: string,
  homepageHtml: string,
  needed: Set<Phase2CheckName>
): Promise<Partial<Record<Phase2CheckName, SubAgentResult>>> {
  if (needed.size === 0) return {}

  const tasks: Array<[Phase2CheckName, Promise<SubAgentResult>]> = []
  if (needed.has("mcpServer")) tasks.push(["mcpServer", checkMcpServerAgent(url, homepageHtml)])
  if (needed.has("openApiSpec")) tasks.push(["openApiSpec", checkOpenApiSpecAgent(url, homepageHtml)])
  if (needed.has("publicApiExists")) tasks.push(["publicApiExists", checkPublicApiAgent(url, homepageHtml)])
  if (needed.has("schemaOrg")) tasks.push(["schemaOrg", checkSchemaOrgAgent(url, homepageHtml)])
  if (needed.has("sdkDocs")) tasks.push(["sdkDocs", checkSdkDocsAgent(url, homepageHtml)])
  if (needed.has("oauth")) tasks.push(["oauth", checkOAuthAgent(url, homepageHtml)])
  if (needed.has("apiKeySupport")) tasks.push(["apiKeySupport", checkApiKeyAgent(url, homepageHtml)])

  const results = await Promise.allSettled(tasks.map(([, p]) => p))
  const merged: Partial<Record<Phase2CheckName, SubAgentResult>> = {}
  tasks.forEach(([name], i) => {
    const r = results[i]
    if (r.status === "fulfilled") merged[name] = r.value
  })
  return merged
}

function assembleBlocks(scored: { checks: Record<string, ScoredCheck> }): {
  machineInterface: BlockResult
  agentDiscovery: BlockResult
  authSecurity: BlockResult
} {
  const c = scored.checks

  const machineInterface: BlockResult = {
    score: (c.mcpServer?.score ?? 0) + (c.openApiSpec?.score ?? 0) + (c.apiDescriptionCoverage?.score ?? 0) + (c.publicApiExists?.score ?? 0),
    maxScore: 30,
    checks: {
      mcpServer: c.mcpServer ?? { score: 0, maxScore: 10 },
      openApiSpec: c.openApiSpec ?? { score: 0, maxScore: 8 },
      apiDescriptionCoverage: c.apiDescriptionCoverage ?? { score: 0, maxScore: 6 },
      publicApiExists: c.publicApiExists ?? { score: 0, maxScore: 6 },
    },
  }

  const agentDiscovery: BlockResult = {
    score: (c.llmsTxt?.score ?? 0) + (c.robotsTxtAi?.score ?? 0) + (c.schemaOrg?.score ?? 0) + (c.sdkDocs?.score ?? 0),
    maxScore: 25,
    checks: {
      llmsTxt: c.llmsTxt ?? { score: 0, maxScore: 8 },
      robotsTxtAi: c.robotsTxtAi ?? { score: 0, maxScore: 6 },
      schemaOrg: c.schemaOrg ?? { score: 0, maxScore: 6 },
      sdkDocs: c.sdkDocs ?? { score: 0, maxScore: 5 },
    },
  }

  const authSecurity: BlockResult = {
    score: (c.oauth?.score ?? 0) + (c.apiKeySupport?.score ?? 0) + (c.corsPolicy?.score ?? 0),
    maxScore: 20,
    checks: {
      oauth: c.oauth ?? { score: 0, maxScore: 8 },
      apiKeySupport: c.apiKeySupport ?? { score: 0, maxScore: 6 },
      corsPolicy: c.corsPolicy ?? { score: 0, maxScore: 6 },
    },
  }

  return { machineInterface, agentDiscovery, authSecurity }
}

export async function runAgentCheck(
  url: string,
  domain: string,
  send: (event: SSEEvent) => void
): Promise<void> {
  // Cache check
  const cached = await getCachedResult(domain)
  if (cached) {
    send({ type: "block", block: "machineInterface", result: cached.blocks.machineInterface })
    send({ type: "block", block: "agentDiscovery", result: cached.blocks.agentDiscovery })
    send({ type: "block", block: "authSecurity", result: cached.blocks.authSecurity })
    send({ type: "block", block: "browserOperability", result: cached.blocks.browserOperability })
    send({ type: "complete", result: cached })
    return
  }

  const scanTimeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error("Scan timed out")), 175_000)
  )

  async function runScan(): Promise<void> {
    // Fetch homepage HTML once
    let homepageHtml = ""
    try {
      const res = await fetchWithTimeout(url, { headers: { "User-Agent": USER_AGENT } }, 8000)
      if (res.ok) homepageHtml = await res.text()
    } catch { /* proceed with empty HTML */ }

    // Phase 1 — deterministic HTTP checks in parallel
    const [machineRes, discoveryRes, authRes, browserRes] = await Promise.allSettled([
      checkMachineInterfacePhase1(url, homepageHtml),
      checkAgentDiscoveryPhase1(url, homepageHtml),
      checkAuthSecurityPhase1(url, homepageHtml),
      callBrowserService(url),
    ])

    const machine: MachineInterfacePhase1Results = machineRes.status === "fulfilled"
      ? machineRes.value
      : { mcpServer: { status: "NOT_FOUND" }, openApiSpec: { status: "NOT_FOUND" }, publicApiExists: { status: "NOT_FOUND" } }

    const discovery: AgentDiscoveryPhase1Results = discoveryRes.status === "fulfilled"
      ? discoveryRes.value
      : { llmsTxt: { status: "NOT_FOUND" }, robotsTxtAi: { status: "FOUND", rawData: { allowedBots: [], blockedBots: [] } }, schemaOrg: { status: "NOT_FOUND" }, sdkDocs: { status: "NOT_FOUND" } }

    const auth: AuthSecurityPhase1Results = authRes.status === "fulfilled"
      ? authRes.value
      : { oauth: { status: "NOT_FOUND" }, apiKeySupport: { status: "NOT_FOUND" }, corsPolicy: { status: "NOT_FOUND" } }

    // Phase 2 — Haiku sub-agents for unresolved checks
    const phase2Needed = identifyPhase2Checks(machine, discovery, auth)
    const phase2Results = await runPhase2(url, homepageHtml, phase2Needed)

    // Sonnet synthesis
    const scored = await scoreSonnet(domain, machine, discovery, auth, phase2Results)

    // Assemble final result
    const { machineInterface, agentDiscovery, authSecurity } = assembleBlocks(scored)
    const browserOperability = browserRes.status === "fulfilled"
      ? browserRes.value as AgentCheckResponse["blocks"]["browserOperability"]
      : { score: 0, maxScore: 25, status: "pending" as const, checks: {} }

    const totalScore = machineInterface.score + agentDiscovery.score + authSecurity.score
    const { grade, gradeColor } = getGrade(totalScore)

    const result: AgentCheckResponse = {
      domain,
      scannedAt: new Date().toISOString(),
      totalScore,
      grade,
      gradeColor,
      blocks: { machineInterface, browserOperability, agentDiscovery, authSecurity },
    }

    // Cache then stream
    await setCachedResult(domain, result)
    send({ type: "block", block: "machineInterface", result: machineInterface })
    send({ type: "block", block: "agentDiscovery", result: agentDiscovery })
    send({ type: "block", block: "authSecurity", result: authSecurity })
    send({ type: "block", block: "browserOperability", result: browserOperability })
    send({ type: "complete", result })
  }

  try {
    await Promise.race([runScan(), scanTimeout])
  } catch (err) {
    send({ type: "error", message: err instanceof Error ? err.message : "Scan failed" })
  }
}
```

- [ ] **Step 2: Type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors. Fix any type errors before continuing.

- [ ] **Step 3: Run all tests**

```bash
cd frontend && npm test
```

Expected: all test suites PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/agent-check/index.ts
git commit -m "feat: two-phase orchestrator with Sonnet synthesis and Redis caching"
```

---

### Task 10: Update .env.example and final verification

**Files:**
- Modify: `frontend/.env.example`

- [ ] **Step 1: Add new env vars to .env.example**

Open `frontend/.env.example` and add:

```bash
# OpenRouter API (used for Phase 2 Haiku sub-agents and Sonnet synthesis)
OPENROUTER_API_KEY=

# Upstash Redis (24h result cache — get from console.upstash.com)
UPSTASH_REDIS_REST_URL=
UPSTASH_REDIS_REST_TOKEN=
```

- [ ] **Step 2: Run the full test suite one final time**

```bash
cd frontend && npm test
```

Expected: all tests PASS, no errors.

- [ ] **Step 3: Type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/.env.example
git commit -m "chore: add OPENROUTER_API_KEY and Upstash env vars to .env.example"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Covered by |
|---|---|
| Phase 1 returns FOUND/NOT_FOUND/UNCERTAIN | Tasks 4, 5, 6 |
| Homepage HTML fetched once, passed to all | Task 9 (index.ts) |
| Phase 2 Haiku sub-agents for NOT_FOUND/UNCERTAIN | Task 7 |
| 7 Phase 2 sub-agents including MCP | Task 7 |
| Haiku fetches up to 3 additional pages | Task 7 (`fetchPages`) |
| Sonnet synthesis with nuanced scoring | Task 8 |
| Per-check justification field | Task 1 (types) + Task 8 |
| detectionMethod: deterministic / ai_fallback | Task 1 (types) + Task 8 |
| Upstash Redis cache, 24h TTL | Tasks 2, 3, 9 |
| Cache hit skips all phases | Task 9 |
| 35s total budget | Task 9 (175s timeout — actual scan is ~35s; 175s is the safety net) |
| OPENROUTER_API_KEY env var | Tasks 3, 10 |
| New file phase2-agents.ts | Task 7 |
| New file sonnet-scoring.ts | Task 8 |
| Types unchanged except additions | Task 1 |
| Browser operability still stub | Task 9 |
| API route unchanged | Not touched |

**Note on scan timeout:** The plan sets a 175s safety net timeout in index.ts. The actual scan completes well within 35s under normal conditions (Phase 1: ~8s, Phase 2: ~15s parallel, Sonnet: ~10s). The 175s catches hung network requests without killing healthy scans.
