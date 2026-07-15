# Agent Operability Report — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the `/agent-report` section to the existing AEO Grader Next.js frontend — a new tool that scores how "agentic-ready" a platform is across 4 blocks of static HTTP/HTML checks, with SSE streaming progress, and a Playwright service skeleton for future browser checks.

**Architecture:** All check logic lives in Next.js API routes (`/api/agent-check`). The results page (`/agent-report/[domain]`) re-scans on every load and receives real-time block-by-block progress via SSE streaming using `fetch` + `ReadableStream`. No Python backend changes; no database; deploys purely on Vercel. A separate Express Playwright service skeleton lives at `/playwright-service/` for future V1 headless browser checks.

**Tech Stack:** Next.js 15 App Router, TypeScript strict mode, Tailwind CSS, Vitest for unit tests, Express.js (Playwright service skeleton)

---

## File Map

**Create (frontend):**
- `frontend/vitest.config.ts`
- `frontend/lib/agent-check/types.ts`
- `frontend/lib/agent-check/utils.ts` + `frontend/lib/agent-check/__tests__/utils.test.ts`
- `frontend/lib/agent-check/scoring.ts` + `frontend/lib/agent-check/__tests__/scoring.test.ts`
- `frontend/lib/agent-check/machine-interface.ts` + `__tests__/machine-interface.test.ts`
- `frontend/lib/agent-check/browser-operability.ts`
- `frontend/lib/agent-check/agent-discovery.ts` + `__tests__/agent-discovery.test.ts`
- `frontend/lib/agent-check/auth-security.ts` + `__tests__/auth-security.test.ts`
- `frontend/lib/agent-check/index.ts`
- `frontend/app/api/agent-check/route.ts`
- `frontend/app/agent-report/page.tsx`
- `frontend/app/agent-report/AgentReportForm.tsx`
- `frontend/app/agent-report/[domain]/page.tsx`
- `frontend/app/agent-report/[domain]/loading.tsx`
- `frontend/components/agent-report/ScanProgress.tsx`
- `frontend/components/agent-report/ScoreHero.tsx`
- `frontend/components/agent-report/BlockCard.tsx`
- `frontend/components/agent-report/CheckItem.tsx`
- `frontend/components/agent-report/BlockDetail.tsx`
- `frontend/components/agent-report/PendingBlock.tsx`
- `frontend/components/agent-report/ReportLayout.tsx`

**Create (Playwright service):**
- `playwright-service/src/types.ts`
- `playwright-service/src/index.ts`
- `playwright-service/package.json`
- `playwright-service/tsconfig.json`
- `playwright-service/Dockerfile`
- `playwright-service/README.md`
- `playwright-service/.env.example`

**Modify:**
- `frontend/package.json` — add vitest scripts + devDependencies
- `frontend/tailwind.config.ts` — add `./app/agent-report/**` to content (already covered by `./app/**`)
- `docker-compose.yml` — add `playwright` service, add `PLAYWRIGHT_SERVICE_URL` to `frontend`
- `frontend/.env.example` (create if absent) — add `PLAYWRIGHT_SERVICE_URL` and `NEXT_PUBLIC_SITE_URL`

---

## Task 1: Setup Vitest

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`

- [ ] **Step 1: Install vitest**

```bash
cd frontend && npm install --save-dev vitest@^1.6.0 @vitest/coverage-v8@^1.6.0
```

Expected: `package.json` devDependencies now includes `vitest` and `@vitest/coverage-v8`.

- [ ] **Step 2: Add test scripts to package.json**

Add to the `"scripts"` section in `frontend/package.json`:
```json
"test": "vitest run",
"test:watch": "vitest"
```

Final scripts block:
```json
"scripts": {
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "lint": "next lint",
  "test": "vitest run",
  "test:watch": "vitest"
}
```

- [ ] **Step 3: Create vitest.config.ts**

Create `frontend/vitest.config.ts`:
```typescript
import { defineConfig } from "vitest/config"
import path from "path"

export default defineConfig({
  test: {
    environment: "node",
    globals: true,
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
})
```

- [ ] **Step 4: Verify vitest runs**

```bash
cd frontend && npm test
```

Expected output: `No test files found` (or similar — zero tests, zero failures). Exit code 0.

- [ ] **Step 5: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts
git commit -m "chore: add vitest to frontend"
```

---

## Task 2: TypeScript Types

**Files:**
- Create: `frontend/lib/agent-check/types.ts`

No unit tests — types are validated by the TypeScript compiler throughout the project.

- [ ] **Step 1: Create types.ts**

Create `frontend/lib/agent-check/types.ts`:
```typescript
export interface CheckResult {
  score: number
  maxScore: number
  found?: boolean
  url?: string
  evidence?: string
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

// Full type definitions for Block 2 — used by the Playwright service in V1.0
export interface BrowserOperabilityChecks {
  semanticHtml: CheckResult      // 7 pts
  ariaAttributes: CheckResult    // 5 pts
  stableUrls: CheckResult        // 5 pts
  keyboardNavigation: CheckResult // 4 pts
  noCaptcha: CheckResult         // 4 pts
}

export interface BrowserOperabilityResult extends BlockResult {
  status: "pending" | "complete"
  checks: Record<keyof BrowserOperabilityChecks, CheckResult>
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/agent-check/types.ts
git commit -m "feat(agent-report): add TypeScript types"
```

---

## Task 3: Utilities

**Files:**
- Create: `frontend/lib/agent-check/utils.ts`
- Create: `frontend/lib/agent-check/__tests__/utils.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/lib/agent-check/__tests__/utils.test.ts`:
```typescript
import { describe, it, expect, beforeEach } from "vitest"
import { normalizeUrl, checkRateLimit } from "../utils"

describe("normalizeUrl", () => {
  it("adds https:// when no scheme given", () => {
    const { url, domain } = normalizeUrl("stripe.com")
    expect(url).toBe("https://stripe.com")
    expect(domain).toBe("stripe.com")
  })

  it("strips www from domain", () => {
    const { domain } = normalizeUrl("https://www.github.com")
    expect(domain).toBe("github.com")
  })

  it("strips path, keeps origin only", () => {
    const { url } = normalizeUrl("https://stripe.com/docs/api")
    expect(url).toBe("https://stripe.com")
  })

  it("preserves https scheme", () => {
    const { url } = normalizeUrl("https://api.example.com")
    expect(url).toBe("https://api.example.com")
    expect(normalizeUrl("https://api.example.com").domain).toBe("example.com")
  })

  it("throws on clearly invalid input", () => {
    expect(() => normalizeUrl("not a url at all !!!")).toThrow()
  })
})

describe("checkRateLimit", () => {
  // Each test uses a unique IP to avoid cross-test state
  it("allows first request", () => {
    expect(checkRateLimit("1.1.1.1")).toBe(true)
  })

  it("blocks when limit exceeded", () => {
    const ip = "2.2.2.2"
    for (let i = 0; i < 10; i++) checkRateLimit(ip)
    expect(checkRateLimit(ip)).toBe(false)
  })

  it("allows up to the limit", () => {
    const ip = "3.3.3.3"
    for (let i = 0; i < 9; i++) checkRateLimit(ip)
    expect(checkRateLimit(ip)).toBe(true) // 10th request — allowed
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/utils.test.ts
```

Expected: FAIL — module `../utils` not found.

- [ ] **Step 3: Implement utils.ts**

Create `frontend/lib/agent-check/utils.ts`:
```typescript
export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = 8000
): Promise<Response> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    clearTimeout(id)
  }
}

export function normalizeUrl(input: string): { url: string; domain: string } {
  const withScheme = /^https?:\/\//i.test(input.trim()) ? input.trim() : `https://${input.trim()}`
  const parsed = new URL(withScheme)
  const domain = parsed.hostname.replace(/^www\./, "")
  return { url: `${parsed.protocol}//${parsed.host}`, domain }
}

const rateLimitMap = new Map<string, number[]>()

export function checkRateLimit(ip: string, maxPerHour = 10): boolean {
  const now = Date.now()
  const windowMs = 60 * 60 * 1000
  const timestamps = (rateLimitMap.get(ip) ?? []).filter(t => now - t < windowMs)
  if (timestamps.length >= maxPerHour) return false
  rateLimitMap.set(ip, [...timestamps, now])
  return true
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/utils.test.ts
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/agent-check/utils.ts frontend/lib/agent-check/__tests__/utils.test.ts
git commit -m "feat(agent-report): add fetch/normalizeUrl/rateLimit utilities"
```

---

## Task 4: Scoring

**Files:**
- Create: `frontend/lib/agent-check/scoring.ts`
- Create: `frontend/lib/agent-check/__tests__/scoring.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/lib/agent-check/__tests__/scoring.test.ts`:
```typescript
import { describe, it, expect } from "vitest"
import { getGrade } from "../scoring"

describe("getGrade", () => {
  it("returns Not Agent Ready for 0", () => {
    expect(getGrade(0)).toEqual({ grade: "Not Agent Ready", gradeColor: "#ef4444" })
  })
  it("returns Not Agent Ready for 25", () => {
    expect(getGrade(25).grade).toBe("Not Agent Ready")
  })
  it("returns Early Stage for 26", () => {
    expect(getGrade(26).grade).toBe("Early Stage")
  })
  it("returns Early Stage for 50", () => {
    expect(getGrade(50).grade).toBe("Early Stage")
  })
  it("returns Agent Friendly for 51", () => {
    expect(getGrade(51).grade).toBe("Agent Friendly")
  })
  it("returns Agent Friendly for 75", () => {
    expect(getGrade(75).grade).toBe("Agent Friendly")
  })
  it("returns Agent Ready for 76", () => {
    expect(getGrade(76).grade).toBe("Agent Ready")
  })
  it("returns Agent Ready for 90", () => {
    expect(getGrade(90).grade).toBe("Agent Ready")
  })
  it("returns Agent Native for 91", () => {
    expect(getGrade(91).grade).toBe("Agent Native")
  })
  it("returns Agent Native for 100", () => {
    expect(getGrade(100)).toEqual({ grade: "Agent Native", gradeColor: "#3b82f6" })
  })
})
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/scoring.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement scoring.ts**

Create `frontend/lib/agent-check/scoring.ts`:
```typescript
interface GradeInfo {
  grade: string
  gradeColor: string
}

export function getGrade(score: number): GradeInfo {
  if (score >= 91) return { grade: "Agent Native",    gradeColor: "#3b82f6" }
  if (score >= 76) return { grade: "Agent Ready",     gradeColor: "#22c55e" }
  if (score >= 51) return { grade: "Agent Friendly",  gradeColor: "#eab308" }
  if (score >= 26) return { grade: "Early Stage",     gradeColor: "#f97316" }
  return           { grade: "Not Agent Ready",        gradeColor: "#ef4444" }
}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/scoring.test.ts
```

Expected: all 10 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/agent-check/scoring.ts frontend/lib/agent-check/__tests__/scoring.test.ts
git commit -m "feat(agent-report): add grade scoring"
```

---

## Task 5: Block 1 — Machine Interface

**Files:**
- Create: `frontend/lib/agent-check/machine-interface.ts`
- Create: `frontend/lib/agent-check/__tests__/machine-interface.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/lib/agent-check/__tests__/machine-interface.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkMachineInterface } from "../machine-interface"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } })
}
function notFound(): Response {
  return new Response("Not Found", { status: 404 })
}

beforeEach(() => mockFetch.mockReset())

describe("checkMachineInterface", () => {
  it("awards 10 pts when /.well-known/mcp.json returns 200", async () => {
    // First call = /.well-known/mcp.json (200), then remaining calls return 404
    mockFetch.mockResolvedValueOnce(ok({}))
    mockFetch.mockResolvedValue(notFound())

    const result = await checkMachineInterface("https://example.com")
    expect(result.checks.mcpServer.score).toBe(10)
    expect((result.checks.mcpServer as { found: boolean }).found).toBe(true)
  })

  it("awards 8 pts for OpenAPI spec with paths", async () => {
    mockFetch.mockResolvedValueOnce(notFound()) // mcp.json
    mockFetch.mockResolvedValueOnce(notFound()) // ai-plugin.json
    mockFetch.mockResolvedValueOnce(notFound()) // mcp.so
    // openapi paths — first one returns valid spec
    mockFetch.mockResolvedValueOnce(
      ok({ openapi: "3.0.0", paths: { "/users": { get: { summary: "List users" } } } })
    )
    mockFetch.mockResolvedValue(notFound())

    const result = await checkMachineInterface("https://example.com")
    expect(result.checks.openApiSpec.score).toBe(8)
  })

  it("awards 4 pts for minimal OpenAPI (no paths)", async () => {
    mockFetch.mockResolvedValueOnce(notFound())
    mockFetch.mockResolvedValueOnce(notFound())
    mockFetch.mockResolvedValueOnce(notFound())
    mockFetch.mockResolvedValueOnce(ok({ openapi: "3.0.0" })) // no paths
    mockFetch.mockResolvedValue(notFound())

    const result = await checkMachineInterface("https://example.com")
    expect(result.checks.openApiSpec.score).toBe(4)
  })

  it("total maxScore is 30", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkMachineInterface("https://example.com")
    expect(result.maxScore).toBe(30)
    expect(result.score).toBe(0)
  })
})
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/machine-interface.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement machine-interface.ts**

Create `frontend/lib/agent-check/machine-interface.ts`:
```typescript
import { fetchWithTimeout } from "./utils"
import type { BlockResult, CheckResult } from "./types"

const OPENAPI_PATHS = [
  "/openapi.json",
  "/swagger.json",
  "/api-docs",
  "/api/openapi.json",
  "/api/v1/openapi.json",
  "/docs/api.json",
  "/api/swagger.json",
]

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`

type McpResult = CheckResult & { found: boolean; url?: string }
type OpenApiResult = CheckResult & { found: boolean; url?: string }
type CoverageResult = CheckResult & { percentage: number | null }
type PublicApiResult = CheckResult & { found: boolean }

async function checkMcpServer(baseUrl: string): Promise<McpResult> {
  for (const path of ["/.well-known/mcp.json", "/.well-known/ai-plugin.json"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: { "User-Agent": USER_AGENT } })
      if (res.ok) return { score: 10, maxScore: 10, found: true, url: path }
    } catch { /* continue */ }
  }
  try {
    const domain = new URL(baseUrl).hostname.replace(/^www\./, "")
    const res = await fetchWithTimeout(
      `https://mcp.so/api/search?q=${encodeURIComponent(domain)}`,
      { headers: { "User-Agent": USER_AGENT } }
    )
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        return { score: 10, maxScore: 10, found: true, url: "mcp.so registry" }
      }
    }
  } catch { /* continue */ }
  return { score: 0, maxScore: 10, found: false }
}

async function checkOpenApiSpec(baseUrl: string): Promise<{ result: OpenApiResult; spec?: Record<string, unknown> }> {
  const results = await Promise.allSettled(
    OPENAPI_PATHS.map(path =>
      fetchWithTimeout(`${baseUrl}${path}`, { headers: { "User-Agent": USER_AGENT } })
        .then(async res => {
          if (!res.ok) return null
          const data = await res.json().catch(() => null)
          if (!data || typeof data !== "object") return null
          return { path, data: data as Record<string, unknown> }
        })
        .catch(() => null)
    )
  )

  for (const r of results) {
    if (r.status !== "fulfilled" || !r.value) continue
    const { path, data } = r.value
    if ("paths" in data && data.paths && typeof data.paths === "object" && Object.keys(data.paths).length > 0) {
      return { result: { score: 8, maxScore: 8, found: true, url: path }, spec: data }
    }
    if ("openapi" in data || "swagger" in data) {
      return { result: { score: 4, maxScore: 8, found: true, url: path }, spec: data }
    }
  }
  return { result: { score: 0, maxScore: 8, found: false } }
}

export function computeApiCoverage(spec: Record<string, unknown> | undefined): CoverageResult {
  if (!spec || !("paths" in spec) || !spec.paths || typeof spec.paths !== "object") {
    return { score: 0, maxScore: 6, percentage: null }
  }
  const paths = spec.paths as Record<string, Record<string, { description?: string; summary?: string }>>
  const httpMethods = ["get", "post", "put", "patch", "delete", "head", "options"]
  let total = 0
  let documented = 0
  for (const pathItem of Object.values(paths)) {
    if (!pathItem || typeof pathItem !== "object") continue
    for (const method of httpMethods) {
      const op = pathItem[method]
      if (!op) continue
      total++
      if (op.description?.trim() || op.summary?.trim()) documented++
    }
  }
  if (total === 0) return { score: 0, maxScore: 6, percentage: 0 }
  const pct = documented / total
  const percentage = Math.round(pct * 100)
  if (pct > 0.7) return { score: 6, maxScore: 6, percentage }
  if (pct >= 0.4) return { score: 4, maxScore: 6, percentage }
  if (pct >= 0.1) return { score: 2, maxScore: 6, percentage }
  return { score: 0, maxScore: 6, percentage }
}

async function checkPublicApi(baseUrl: string): Promise<PublicApiResult> {
  let signals = 0
  try {
    const res = await fetchWithTimeout(baseUrl, { headers: { "User-Agent": USER_AGENT } })
    if (res.ok) {
      const html = await res.text()
      if (/href=["'][^"']*\/(developers|api|docs)[^"']*["']/i.test(html)) signals++
      if (/\b(API|Developers|Documentation)\b/.test(html)) signals++
      if (/rel=["']api["']/i.test(html)) signals++
    }
  } catch { /* ignore */ }
  try {
    const res = await fetchWithTimeout(`${baseUrl}/robots.txt`, { headers: { "User-Agent": USER_AGENT } })
    if (res.ok) {
      const txt = await res.text()
      if (/^(?:Allow|Disallow):\s*\/api\//im.test(txt)) signals++
    }
  } catch { /* ignore */ }
  if (signals >= 2) return { score: 6, maxScore: 6, found: true }
  if (signals === 1) return { score: 3, maxScore: 6, found: true }
  return { score: 0, maxScore: 6, found: false }
}

export async function checkMachineInterface(baseUrl: string): Promise<BlockResult> {
  const [mcpRes, openApiRes, publicApiRes] = await Promise.allSettled([
    checkMcpServer(baseUrl),
    checkOpenApiSpec(baseUrl),
    checkPublicApi(baseUrl),
  ])

  const mcpServer = mcpRes.status === "fulfilled" ? mcpRes.value : { score: 0, maxScore: 10, found: false }
  const { result: openApiSpec, spec } = openApiRes.status === "fulfilled"
    ? openApiRes.value
    : { result: { score: 0, maxScore: 8, found: false }, spec: undefined }
  const coverage = computeApiCoverage(spec)
  const publicApi = publicApiRes.status === "fulfilled" ? publicApiRes.value : { score: 0, maxScore: 6, found: false }

  const score = mcpServer.score + openApiSpec.score + coverage.score + publicApi.score

  return {
    score,
    maxScore: 30,
    checks: { mcpServer, openApiSpec, apiDescriptionCoverage: coverage, publicApiExists: publicApi },
  }
}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/machine-interface.test.ts
```

Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/agent-check/machine-interface.ts frontend/lib/agent-check/__tests__/machine-interface.test.ts
git commit -m "feat(agent-report): Block 1 — Machine Interface checks"
```

---

## Task 6: Block 2 — Browser Operability Stub

**Files:**
- Create: `frontend/lib/agent-check/browser-operability.ts`

No unit tests — the function is a trivial stub with an env-var branch; tested visually via the results page.

- [ ] **Step 1: Create browser-operability.ts**

Create `frontend/lib/agent-check/browser-operability.ts`:
```typescript
import type { BlockResult, BrowserOperabilityResult } from "./types"

// TODO: implement with Playwright service in V1.0

const MOCK: BrowserOperabilityResult = {
  score: 0,
  maxScore: 25,
  status: "pending",
  checks: {
    semanticHtml:       { score: 0, maxScore: 7 },
    ariaAttributes:     { score: 0, maxScore: 5 },
    stableUrls:         { score: 0, maxScore: 5 },
    keyboardNavigation: { score: 0, maxScore: 4 },
    noCaptcha:          { score: 0, maxScore: 4 },
  },
}

export async function callBrowserService(_url: string): Promise<BlockResult & { status: "pending" | "complete" }> {
  const serviceUrl = process.env.PLAYWRIGHT_SERVICE_URL
  if (!serviceUrl) return MOCK

  try {
    const res = await fetch(`${serviceUrl}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: _url }),
      signal: AbortSignal.timeout(10000),
    })
    if (!res.ok) return MOCK
    const data = await res.json() as BlockResult
    // Always "pending" until V1.0 — override service status
    return { ...MOCK, ...data, status: "pending" }
  } catch {
    return MOCK
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/agent-check/browser-operability.ts
git commit -m "feat(agent-report): Block 2 — Browser Operability stub + full types"
```

---

## Task 7: Block 3 — Agent Discovery

**Files:**
- Create: `frontend/lib/agent-check/agent-discovery.ts`
- Create: `frontend/lib/agent-check/__tests__/agent-discovery.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/lib/agent-check/__tests__/agent-discovery.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkAgentDiscovery } from "../agent-discovery"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: string, ct = "text/plain"): Response {
  return new Response(body, { status: 200, headers: { "Content-Type": ct } })
}
function notFound(): Response {
  return new Response("Not Found", { status: 404 })
}

beforeEach(() => mockFetch.mockReset())

describe("llms.txt scoring", () => {
  it("awards 0 pts when llms.txt not found", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkAgentDiscovery("https://example.com")
    expect(result.checks.llmsTxt.score).toBe(0)
    expect((result.checks.llmsTxt as { found: boolean }).found).toBe(false)
  })

  it("awards base 2 pts when llms.txt found", async () => {
    // llms.txt = 200, everything else 404
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/llms.txt")) return Promise.resolve(ok("# Hello world"))
      return Promise.resolve(notFound())
    })
    const result = await checkAgentDiscovery("https://example.com")
    expect(result.checks.llmsTxt.score).toBeGreaterThanOrEqual(2)
  })

  it("awards +3 when llms.txt has ## Tools section", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/llms.txt")) return Promise.resolve(ok("# Intro\n## Tools\nsome tool info"))
      return Promise.resolve(notFound())
    })
    const result = await checkAgentDiscovery("https://example.com")
    expect(result.checks.llmsTxt.score).toBeGreaterThanOrEqual(5) // 2 base + 3 sections
    expect((result.checks.llmsTxt as { hasActionSections: boolean }).hasActionSections).toBe(true)
  })
})

describe("robots.txt AI scoring", () => {
  it("awards 6 pts when robots.txt not found (allowed by default)", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkAgentDiscovery("https://example.com")
    expect(result.checks.robotsTxtAi.score).toBe(6)
  })

  it("awards 0 pts when all bots blocked via wildcard Disallow: /", async () => {
    const robotsTxt = "User-agent: *\nDisallow: /"
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/robots.txt")) return Promise.resolve(ok(robotsTxt))
      return Promise.resolve(notFound())
    })
    const result = await checkAgentDiscovery("https://example.com")
    expect(result.checks.robotsTxtAi.score).toBe(0)
  })

  it("awards full pts when bots are not mentioned (allowed by default)", async () => {
    const robotsTxt = "User-agent: Googlebot\nDisallow: /private"
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/robots.txt")) return Promise.resolve(ok(robotsTxt))
      return Promise.resolve(notFound())
    })
    const result = await checkAgentDiscovery("https://example.com")
    expect(result.checks.robotsTxtAi.score).toBe(6)
  })
})

describe("checkAgentDiscovery totals", () => {
  it("maxScore is 25", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkAgentDiscovery("https://example.com")
    expect(result.maxScore).toBe(25)
  })
})
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/agent-discovery.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement agent-discovery.ts**

Create `frontend/lib/agent-check/agent-discovery.ts`:
```typescript
import { fetchWithTimeout } from "./utils"
import type { BlockResult, CheckResult } from "./types"

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }

const AI_BOTS = ["anthropic-ai", "gpt-bot", "claude-bot", "perplexity-bot", "cohere-ai", "google-extended", "amazonbot"]
const ACTION_SECTIONS = ["## api", "## tools", "## actions", "## capabilities", "## integrations"]
const HIGH_VALUE_TYPES = ["WebAPI", "APIReference", "SoftwareApplication", "Action", "EntryPoint"]
const MEDIUM_VALUE_TYPES = ["Service", "Organization", "WebSite", "Product"]

type LlmsResult = CheckResult & { found: boolean; hasActionSections: boolean; wordCount: number }
type RobotsResult = CheckResult & { allowedBots: string[]; blockedBots: string[] }
type SchemaResult = CheckResult & { typesFound: string[] }
type SdkResult = CheckResult & { found: boolean }

async function checkLlmsTxt(baseUrl: string): Promise<LlmsResult> {
  try {
    const res = await fetchWithTimeout(`${baseUrl}/llms.txt`, { headers: HEADERS })
    if (!res.ok) return { score: 0, maxScore: 8, found: false, hasActionSections: false, wordCount: 0 }
    const text = await res.text()
    const lower = text.toLowerCase()
    let score = 2
    if (/^-\s+https?:\/\//m.test(text)) score += 1
    const hasActionSections = ACTION_SECTIONS.some(s => lower.includes(s))
    if (hasActionSections) score += 3
    const wordCount = text.split(/\s+/).filter(Boolean).length
    if (wordCount >= 200) score += 2
    return { score: Math.min(score, 8), maxScore: 8, found: true, hasActionSections, wordCount }
  } catch {
    return { score: 0, maxScore: 8, found: false, hasActionSections: false, wordCount: 0 }
  }
}

async function checkRobotsTxtAi(baseUrl: string): Promise<RobotsResult> {
  try {
    const res = await fetchWithTimeout(`${baseUrl}/robots.txt`, { headers: HEADERS })
    if (!res.ok) return { score: 6, maxScore: 6, allowedBots: [...AI_BOTS], blockedBots: [] }
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
    const blocked = blockedBots.length

    let score: number
    if (blocked === 0) score = 6
    else if (blocked <= 2) score = 4
    else if (blocked <= 4) score = 2
    else score = 0

    return { score, maxScore: 6, allowedBots, blockedBots }
  } catch {
    return { score: 6, maxScore: 6, allowedBots: [...AI_BOTS], blockedBots: [] }
  }
}

async function checkSchemaOrg(baseUrl: string): Promise<SchemaResult> {
  try {
    const res = await fetchWithTimeout(baseUrl, { headers: HEADERS })
    if (!res.ok) return { score: 0, maxScore: 6, typesFound: [] }
    const html = await res.text()
    const ldMatches = [...html.matchAll(/<script[^>]+type=["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script>/gi)]
    const typesFound: string[] = []
    let score = 0

    for (const match of ldMatches) {
      try {
        const data = JSON.parse(match[1])
        const items = Array.isArray(data) ? data : [data]
        for (const item of items) {
          const t = item?.["@type"]
          if (typeof t !== "string" || typesFound.includes(t)) continue
          typesFound.push(t)
          if (HIGH_VALUE_TYPES.includes(t)) score = Math.min(score + 2, 6)
          else if (MEDIUM_VALUE_TYPES.includes(t)) score = Math.min(score + 1, 6)
        }
      } catch { /* malformed JSON-LD */ }
    }
    return { score, maxScore: 6, typesFound }
  } catch {
    return { score: 0, maxScore: 6, typesFound: [] }
  }
}

async function checkSdkDocs(baseUrl: string): Promise<SdkResult> {
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

  const score = signals >= 5 ? 5 : signals >= 3 ? 3 : signals >= 1 ? 1 : 0
  return { score, maxScore: 5, found: signals > 0 }
}

export async function checkAgentDiscovery(baseUrl: string): Promise<BlockResult> {
  const [llmsRes, robotsRes, schemaRes, sdkRes] = await Promise.allSettled([
    checkLlmsTxt(baseUrl),
    checkRobotsTxtAi(baseUrl),
    checkSchemaOrg(baseUrl),
    checkSdkDocs(baseUrl),
  ])

  const checks = {
    llmsTxt: llmsRes.status === "fulfilled" ? llmsRes.value : { score: 0, maxScore: 8, found: false, hasActionSections: false, wordCount: 0 },
    robotsTxtAi: robotsRes.status === "fulfilled" ? robotsRes.value : { score: 6, maxScore: 6, allowedBots: [...AI_BOTS], blockedBots: [] },
    schemaOrg: schemaRes.status === "fulfilled" ? schemaRes.value : { score: 0, maxScore: 6, typesFound: [] },
    sdkDocs: sdkRes.status === "fulfilled" ? sdkRes.value : { score: 0, maxScore: 5, found: false },
  }

  const score = checks.llmsTxt.score + checks.robotsTxtAi.score + checks.schemaOrg.score + checks.sdkDocs.score
  return { score, maxScore: 25, checks }
}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/agent-discovery.test.ts
```

Expected: all 7 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/agent-check/agent-discovery.ts frontend/lib/agent-check/__tests__/agent-discovery.test.ts
git commit -m "feat(agent-report): Block 3 — Agent Discovery checks"
```

---

## Task 8: Block 4 — Auth & Security

**Files:**
- Create: `frontend/lib/agent-check/auth-security.ts`
- Create: `frontend/lib/agent-check/__tests__/auth-security.test.ts`

- [ ] **Step 1: Write failing tests**

Create `frontend/lib/agent-check/__tests__/auth-security.test.ts`:
```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkAuthSecurity } from "../auth-security"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json", ...headers },
  })
}
function notFound(): Response {
  return new Response("Not Found", { status: 404 })
}

beforeEach(() => mockFetch.mockReset())

describe("OAuth detection", () => {
  it("awards 8 pts when /.well-known/oauth-authorization-server returns valid JSON", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("oauth-authorization-server")) return Promise.resolve(ok({ issuer: "https://example.com" }))
      return Promise.resolve(notFound())
    })
    const result = await checkAuthSecurity("https://example.com")
    expect(result.checks.oauth.score).toBe(8)
    expect((result.checks.oauth as { method: string }).method).toBe("well-known")
  })

  it("awards 4 pts when OAuth 2.0 mentioned in /developers HTML", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/developers")) return Promise.resolve(
        new Response("<p>We support OAuth 2.0 flows.</p>", { status: 200 })
      )
      return Promise.resolve(notFound())
    })
    const result = await checkAuthSecurity("https://example.com")
    expect(result.checks.oauth.score).toBe(4)
    expect((result.checks.oauth as { method: string }).method).toBe("docs")
  })

  it("awards 0 pts when OAuth not found", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkAuthSecurity("https://example.com")
    expect(result.checks.oauth.score).toBe(0)
  })
})

describe("CORS detection", () => {
  it("awards 6 pts when Access-Control-Allow-Origin is *", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/api")) return Promise.resolve(
        new Response(null, { status: 200, headers: { "Access-Control-Allow-Origin": "*" } })
      )
      return Promise.resolve(notFound())
    })
    const result = await checkAuthSecurity("https://example.com")
    expect(result.checks.corsPolicy.score).toBe(6)
    expect((result.checks.corsPolicy as { policy: string }).policy).toBe("*")
  })

  it("awards 3 pts when Access-Control-Allow-Origin is a specific domain", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/api")) return Promise.resolve(
        new Response(null, { status: 200, headers: { "Access-Control-Allow-Origin": "https://app.example.com" } })
      )
      return Promise.resolve(notFound())
    })
    const result = await checkAuthSecurity("https://example.com")
    expect(result.checks.corsPolicy.score).toBe(3)
  })
})

describe("checkAuthSecurity totals", () => {
  it("maxScore is 20", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkAuthSecurity("https://example.com")
    expect(result.maxScore).toBe(20)
  })
})
```

- [ ] **Step 2: Run to verify fail**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/auth-security.test.ts
```

Expected: FAIL — module not found.

- [ ] **Step 3: Implement auth-security.ts**

Create `frontend/lib/agent-check/auth-security.ts`:
```typescript
import { fetchWithTimeout } from "./utils"
import type { BlockResult, CheckResult } from "./types"

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }

type OAuthResult = CheckResult & { found: boolean; method: "well-known" | "docs" | null }
type ApiKeyResult = CheckResult & { found: boolean }
type CorsResult = CheckResult & { policy: string | null; status?: "no_api_found" }

async function checkOAuth(baseUrl: string): Promise<OAuthResult> {
  for (const path of ["/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok) {
        await res.json() // validates it's JSON
        return { score: 8, maxScore: 8, found: true, method: "well-known" }
      }
    } catch { /* continue */ }
  }
  for (const path of ["/developers", "/docs", "/api"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok) {
        const html = await res.text()
        if (/oauth\s*2\.?0|openid\s+connect/i.test(html)) {
          return { score: 4, maxScore: 8, found: true, method: "docs" }
        }
      }
    } catch { /* continue */ }
  }
  return { score: 0, maxScore: 8, found: false, method: null }
}

async function checkApiKeySupport(baseUrl: string): Promise<ApiKeyResult> {
  const API_KEY_PATTERN = /api\s*key|api\s*token|access\s+token|personal\s+access\s+token|secret\s+key/i

  for (const path of ["/settings/api", "/account/api", "/api-keys"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok && API_KEY_PATTERN.test(await res.text())) {
        return { score: 6, maxScore: 6, found: true }
      }
    } catch { /* continue */ }
  }
  for (const path of ["/settings", "/account", "/developers", "/"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok && API_KEY_PATTERN.test(await res.text())) {
        return { score: 3, maxScore: 6, found: true }
      }
    } catch { /* continue */ }
  }
  return { score: 0, maxScore: 6, found: false }
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

async function checkCors(baseUrl: string): Promise<CorsResult> {
  const endpoint = await findApiEndpoint(baseUrl)
  if (!endpoint) return { score: 0, maxScore: 6, policy: null, status: "no_api_found" }

  try {
    const res = await fetchWithTimeout(endpoint, {
      method: "OPTIONS",
      headers: {
        ...HEADERS,
        "Origin": "https://test.example.com",
        "Access-Control-Request-Method": "GET",
      },
    })
    const origin = res.headers.get("access-control-allow-origin")
    if (origin === "*") return { score: 6, maxScore: 6, policy: "*" }
    if (origin) return { score: 3, maxScore: 6, policy: origin }
    return { score: 1, maxScore: 6, policy: null }
  } catch {
    return { score: 1, maxScore: 6, policy: null }
  }
}

export async function checkAuthSecurity(baseUrl: string): Promise<BlockResult> {
  const [oauthRes, apiKeyRes, corsRes] = await Promise.allSettled([
    checkOAuth(baseUrl),
    checkApiKeySupport(baseUrl),
    checkCors(baseUrl),
  ])

  const checks = {
    oauth: oauthRes.status === "fulfilled" ? oauthRes.value : { score: 0, maxScore: 8, found: false, method: null as null },
    apiKeySupport: apiKeyRes.status === "fulfilled" ? apiKeyRes.value : { score: 0, maxScore: 6, found: false },
    corsPolicy: corsRes.status === "fulfilled" ? corsRes.value : { score: 0, maxScore: 6, policy: null },
  }

  const score = checks.oauth.score + checks.apiKeySupport.score + checks.corsPolicy.score
  return { score, maxScore: 20, checks }
}
```

- [ ] **Step 4: Run tests to verify pass**

```bash
cd frontend && npm test -- lib/agent-check/__tests__/auth-security.test.ts
```

Expected: all 6 tests PASS.

- [ ] **Step 5: Run all tests**

```bash
cd frontend && npm test
```

Expected: all tests across all modules PASS.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/agent-check/auth-security.ts frontend/lib/agent-check/__tests__/auth-security.test.ts
git commit -m "feat(agent-report): Block 4 — Auth & Security checks"
```

---

## Task 9: Orchestrator

**Files:**
- Create: `frontend/lib/agent-check/index.ts`

- [ ] **Step 1: Create index.ts**

Create `frontend/lib/agent-check/index.ts`:
```typescript
import { checkMachineInterface } from "./machine-interface"
import { callBrowserService } from "./browser-operability"
import { checkAgentDiscovery } from "./agent-discovery"
import { checkAuthSecurity } from "./auth-security"
import { getGrade } from "./scoring"
import type { AgentCheckResponse, BlockResult, SSEEvent } from "./types"

const BLOCK_NAMES = ["machineInterface", "browserOperability", "agentDiscovery", "authSecurity"] as const
type BlockName = typeof BLOCK_NAMES[number]

const EMPTY_BLOCKS: AgentCheckResponse["blocks"] = {
  machineInterface:    { score: 0, maxScore: 30, checks: {} },
  browserOperability:  { score: 0, maxScore: 25, status: "pending", checks: {} },
  agentDiscovery:      { score: 0, maxScore: 25, checks: {} },
  authSecurity:        { score: 0, maxScore: 20, checks: {} },
}

export async function runAgentCheck(
  url: string,
  domain: string,
  send: (event: SSEEvent) => void
): Promise<void> {
  const blocks = { ...EMPTY_BLOCKS }

  const timeout = new Promise<never>((_, reject) =>
    setTimeout(() => reject(new Error("Scan timed out")), 30_000)
  )

  const blockFns = [
    () => checkMachineInterface(url),
    () => callBrowserService(url),
    () => checkAgentDiscovery(url),
    () => checkAuthSecurity(url),
  ]

  const blockPromises = blockFns.map((fn, i) => {
    const name = BLOCK_NAMES[i]
    return fn()
      .then(result => {
        blocks[name] = result as AgentCheckResponse["blocks"][BlockName]
        send({ type: "block", block: name, result: result as BlockResult })
      })
      .catch(() => {
        send({ type: "block", block: name, result: blocks[name] })
      })
  })

  await Promise.race([
    Promise.allSettled(blockPromises),
    timeout,
  ]).catch(() => { /* timeout — send whatever we have */ })

  const totalScore =
    blocks.machineInterface.score +
    blocks.browserOperability.score +
    blocks.agentDiscovery.score +
    blocks.authSecurity.score

  const { grade, gradeColor } = getGrade(totalScore)

  send({
    type: "complete",
    result: {
      domain,
      scannedAt: new Date().toISOString(),
      totalScore,
      grade,
      gradeColor,
      blocks,
    },
  })
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/agent-check/index.ts
git commit -m "feat(agent-report): orchestrator — runs 4 blocks in parallel"
```

---

## Task 10: API Route (SSE)

**Files:**
- Create: `frontend/app/api/agent-check/route.ts`

- [ ] **Step 1: Create route.ts**

Create `frontend/app/api/agent-check/route.ts`:
```typescript
import { type NextRequest } from "next/server"
import { checkRateLimit, normalizeUrl } from "@/lib/agent-check/utils"
import { runAgentCheck } from "@/lib/agent-check/index"
import type { SSEEvent } from "@/lib/agent-check/types"

export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  let body: { url?: string }
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  if (!body.url || typeof body.url !== "string") {
    return Response.json({ error: "url is required" }, { status: 400 })
  }

  let normalized: { url: string; domain: string }
  try {
    normalized = normalizeUrl(body.url)
  } catch {
    return Response.json({ error: "Invalid URL" }, { status: 400 })
  }

  const ip =
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    req.headers.get("x-real-ip") ??
    "unknown"

  if (!checkRateLimit(ip)) {
    return Response.json({ error: "Rate limit exceeded. Max 10 scans per hour." }, { status: 429 })
  }

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      function send(event: SSEEvent) {
        try {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
        } catch { /* client disconnected */ }
      }

      try {
        await runAgentCheck(normalized.url, normalized.domain, send)
      } catch (err) {
        send({ type: "error", message: err instanceof Error ? err.message : "Scan failed" })
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  })
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Manual smoke test**

Start the dev server and POST to the endpoint:
```bash
cd frontend && npm run dev
# In another terminal:
curl -X POST http://localhost:3000/api/agent-check \
  -H "Content-Type: application/json" \
  -d '{"url":"stripe.com"}' \
  -N
```

Expected: a stream of `data: {...}` lines ending with `data: {"type":"complete",...}`.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/api/agent-check/route.ts
git commit -m "feat(agent-report): SSE API route /api/agent-check"
```

---

## Task 11: UI Components

**Files:**
- Create: `frontend/components/agent-report/ScanProgress.tsx`
- Create: `frontend/components/agent-report/ScoreHero.tsx`
- Create: `frontend/components/agent-report/BlockCard.tsx`
- Create: `frontend/components/agent-report/CheckItem.tsx`
- Create: `frontend/components/agent-report/BlockDetail.tsx`
- Create: `frontend/components/agent-report/PendingBlock.tsx`
- Create: `frontend/components/agent-report/ReportLayout.tsx`

- [ ] **Step 1: Create ScanProgress.tsx**

Create `frontend/components/agent-report/ScanProgress.tsx`:
```tsx
const STEPS = [
  { key: "machineInterface",   label: "Checking machine interfaces" },
  { key: "browserOperability", label: "Browser operability (stub)" },
  { key: "agentDiscovery",     label: "Analyzing agent discovery" },
  { key: "authSecurity",       label: "Testing auth & security" },
] as const

interface Props {
  domain: string
  completedBlocks: Set<string>
}

export default function ScanProgress({ domain, completedBlocks }: Props) {
  return (
    <div className="space-y-8 py-12">
      <p className="text-xl font-medium text-neutral-700">Scanning {domain}…</p>
      <div className="space-y-4">
        {STEPS.map(step => {
          const done = completedBlocks.has(step.key)
          return (
            <div key={step.key} className="flex items-center gap-3">
              <span className={`text-base ${done ? "text-green-500" : "text-neutral-300"}`}>
                {done ? "●" : "○"}
              </span>
              <span className={`text-sm ${done ? "text-neutral-900" : "text-neutral-400"}`}>
                {step.label}
              </span>
              {done && <span className="ml-auto text-xs text-green-600">done</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
```

- [ ] **Step 2: Create ScoreHero.tsx**

Create `frontend/components/agent-report/ScoreHero.tsx`:
```tsx
interface Props {
  domain: string
  totalScore: number
  grade: string
  gradeColor: string
  scannedAt: string
}

export default function ScoreHero({ domain, totalScore, grade, gradeColor, scannedAt }: Props) {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-neutral-50 px-6 py-10 sm:px-10 sm:py-14">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-neutral-500">Agent Operability Score</p>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="text-7xl font-semibold tracking-tight sm:text-8xl" style={{ color: gradeColor }}>
              {totalScore}
            </span>
            <span className="text-2xl text-neutral-400">/ 100</span>
          </div>
          <p className="mt-2 text-sm text-neutral-500">{domain}</p>
        </div>
        <div className="text-left sm:text-right">
          <span
            className="inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ring-1 ring-inset"
            style={{
              color: gradeColor,
              borderColor: gradeColor + "55",
              backgroundColor: gradeColor + "15",
            }}
          >
            {grade}
          </span>
          <p className="mt-3 text-xs text-neutral-400">
            Scanned {new Date(scannedAt).toLocaleDateString("en-GB")}
          </p>
        </div>
      </div>
    </section>
  )
}
```

- [ ] **Step 3: Create BlockCard.tsx**

Create `frontend/components/agent-report/BlockCard.tsx`:
```tsx
interface Props {
  title: string
  score: number
  maxScore: number
  isPending?: boolean
}

export default function BlockCard({ title, score, maxScore, isPending = false }: Props) {
  const pct = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0
  const barColor = pct >= 75 ? "#22c55e" : pct >= 40 ? "#eab308" : "#ef4444"

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-5">
      <p className="text-xs font-medium text-neutral-600">{title}</p>
      {isPending ? (
        <p className="mt-3 text-xs text-neutral-400">Coming soon</p>
      ) : (
        <>
          <p className="mt-2 text-2xl font-semibold text-neutral-900">
            {score}{" "}
            <span className="text-sm font-normal text-neutral-400">/ {maxScore}</span>
          </p>
          <div className="mt-3 h-1.5 w-full rounded-full bg-neutral-100">
            <div
              className="h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${pct}%`, backgroundColor: barColor }}
            />
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create CheckItem.tsx**

Create `frontend/components/agent-report/CheckItem.tsx`:
```tsx
import type { CheckResult } from "@/lib/agent-check/types"

interface Props {
  name: string
  result: CheckResult
}

export default function CheckItem({ name, result }: Props) {
  const { score, maxScore, evidence, url } = result
  const full = score > 0 && score === maxScore
  const partial = score > 0 && score < maxScore
  const iconClass = full ? "text-green-500" : partial ? "text-yellow-500" : "text-red-400"
  const icon = full ? "✓" : partial ? "~" : "✗"

  return (
    <div className="flex items-start gap-3 border-b border-neutral-100 py-2.5 last:border-0">
      <span className={`mt-0.5 w-4 flex-shrink-0 text-sm font-semibold ${iconClass}`}>{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-neutral-800">{name}</p>
        {(evidence ?? url) && (
          <p className="mt-0.5 truncate text-xs text-neutral-500">{evidence ?? url}</p>
        )}
      </div>
      <span className="whitespace-nowrap text-xs text-neutral-500">
        {score} / {maxScore}
      </span>
    </div>
  )
}
```

- [ ] **Step 5: Create BlockDetail.tsx**

Create `frontend/components/agent-report/BlockDetail.tsx`:
```tsx
"use client"
import { useState } from "react"
import type { BlockResult } from "@/lib/agent-check/types"
import CheckItem from "./CheckItem"

const CHECK_LABELS: Record<string, string> = {
  mcpServer:              "MCP Server",
  openApiSpec:            "OpenAPI Specification",
  apiDescriptionCoverage: "API Description Coverage",
  publicApiExists:        "Public API",
  llmsTxt:                "llms.txt Quality",
  robotsTxtAi:            "Robots.txt AI Permissions",
  schemaOrg:              "Schema.org Markup",
  sdkDocs:                "SDK Documentation",
  oauth:                  "OAuth 2.0 Support",
  apiKeySupport:          "API Key / Token Support",
  corsPolicy:             "CORS Policy",
}

interface Props {
  title: string
  block: BlockResult
}

export default function BlockDetail({ title, block }: Props) {
  const [open, setOpen] = useState(true)

  return (
    <section className="rounded-2xl border border-neutral-200 bg-white">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between px-6 py-4 text-left"
        aria-expanded={open}
      >
        <span className="font-semibold text-neutral-900">{title}</span>
        <span className="text-xs text-neutral-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="border-t border-neutral-100 px-6 py-2">
          {Object.entries(block.checks).map(([key, result]) => (
            <CheckItem key={key} name={CHECK_LABELS[key] ?? key} result={result} />
          ))}
          {Object.keys(block.checks).length === 0 && (
            <p className="py-4 text-sm text-neutral-400">No checks ran for this block.</p>
          )}
        </div>
      )}
    </section>
  )
}
```

- [ ] **Step 6: Create PendingBlock.tsx**

Create `frontend/components/agent-report/PendingBlock.tsx`:
```tsx
export default function PendingBlock() {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-white px-6 py-8">
      <p className="font-semibold text-neutral-900">Browser Operability Scan</p>
      <p className="mt-2 max-w-lg text-sm text-neutral-500">
        Coming soon — we&apos;re adding headless browser analysis to check semantic HTML,
        ARIA attributes, stable URLs, keyboard navigation, and CAPTCHA presence.
      </p>
      <div className="mt-4 h-1.5 w-full rounded-full bg-neutral-100">
        <div className="h-1.5 w-0 rounded-full bg-neutral-200" />
      </div>
    </section>
  )
}
```

- [ ] **Step 7: Create ReportLayout.tsx**

Create `frontend/components/agent-report/ReportLayout.tsx`:
```tsx
"use client"
import Link from "next/link"
import type { AgentCheckResponse } from "@/lib/agent-check/types"
import ScoreHero from "./ScoreHero"
import BlockCard from "./BlockCard"
import BlockDetail from "./BlockDetail"
import PendingBlock from "./PendingBlock"

const BLOCK_TITLES = {
  machineInterface:   "Machine Interface",
  browserOperability: "Browser Operability",
  agentDiscovery:     "Agent Discovery",
  authSecurity:       "Auth & Security",
} as const

interface Props {
  result: AgentCheckResponse
}

export default function ReportLayout({ result }: Props) {
  function copyLink() {
    navigator.clipboard.writeText(window.location.href).catch(() => {})
  }

  return (
    <div className="space-y-6">
      <ScoreHero
        domain={result.domain}
        totalScore={result.totalScore}
        grade={result.grade}
        gradeColor={result.gradeColor}
        scannedAt={result.scannedAt}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(Object.keys(BLOCK_TITLES) as Array<keyof typeof BLOCK_TITLES>).map(key => (
          <BlockCard
            key={key}
            title={BLOCK_TITLES[key]}
            score={result.blocks[key].score}
            maxScore={result.blocks[key].maxScore}
            isPending={key === "browserOperability"}
          />
        ))}
      </div>

      <BlockDetail title="Machine Interface"  block={result.blocks.machineInterface} />
      <PendingBlock />
      <BlockDetail title="Agent Discovery"    block={result.blocks.agentDiscovery} />
      <BlockDetail title="Auth & Security"    block={result.blocks.authSecurity} />

      <div className="flex flex-wrap gap-3 border-t border-neutral-200 pt-4 print-hide">
        <button
          onClick={copyLink}
          className="rounded-lg border border-neutral-300 px-4 py-2 text-sm text-neutral-700 transition hover:bg-neutral-50"
        >
          Share this report
        </button>
        <Link
          href="/agent-report"
          className="rounded-lg border border-neutral-300 px-4 py-2 text-sm text-neutral-700 transition hover:bg-neutral-50"
        >
          Scan another site
        </Link>
        <Link
          href="/"
          className="rounded-lg border border-neutral-300 px-4 py-2 text-sm text-neutral-700 transition hover:bg-neutral-50"
        >
          Check AI visibility →
        </Link>
      </div>
    </div>
  )
}
```

- [ ] **Step 8: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 9: Commit**

```bash
git add frontend/components/agent-report/
git commit -m "feat(agent-report): UI components (ScoreHero, BlockCard, CheckItem, BlockDetail, PendingBlock, ScanProgress, ReportLayout)"
```

---

## Task 12: Landing Page

**Files:**
- Create: `frontend/app/agent-report/page.tsx`
- Create: `frontend/app/agent-report/AgentReportForm.tsx`

- [ ] **Step 1: Create AgentReportForm.tsx (client component)**

Create `frontend/app/agent-report/AgentReportForm.tsx`:
```tsx
"use client"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { normalizeUrl } from "@/lib/agent-check/utils"

export default function AgentReportForm() {
  const router = useRouter()
  const [url, setUrl] = useState("")
  const [error, setError] = useState<string | null>(null)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const { domain } = normalizeUrl(url.trim())
      router.push(`/agent-report/${encodeURIComponent(domain)}`)
    } catch {
      setError("Enter a valid URL — e.g. stripe.com")
    }
  }

  return (
    <form onSubmit={onSubmit} className="w-full max-w-xl space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="stripe.com or https://stripe.com"
          className="flex-1 rounded-lg border border-neutral-300 px-4 py-3 text-base outline-none focus:border-neutral-900"
          required
        />
        <button
          type="submit"
          disabled={!url.trim()}
          className="rounded-lg bg-neutral-900 px-6 py-3 text-base font-medium text-white transition hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Analyze
        </button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <p className="text-xs text-neutral-500">Scan takes ~15–30 seconds.</p>
    </form>
  )
}
```

- [ ] **Step 2: Create page.tsx (server component)**

Create `frontend/app/agent-report/page.tsx`:
```tsx
import type { Metadata } from "next"
import AgentReportForm from "./AgentReportForm"

export const metadata: Metadata = {
  title: "Agent Operability Report",
  description: "Find out if AI agents can actually work with your platform — not just find it.",
}

export default function AgentReportPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center p-8">
      <div className="space-y-6">
        <header className="space-y-3">
          <h1 className="text-5xl font-semibold tracking-tight">Agent Operability Report</h1>
          <p className="max-w-xl text-lg text-neutral-600">
            Find out if AI agents can actually work with your platform — not just find it.
            We check for MCP servers, OpenAPI specs, OAuth support, and more.
          </p>
        </header>
        <AgentReportForm />
        <p className="text-sm text-neutral-500">
          Also check your AI visibility{" "}
          <a href="/" className="underline hover:text-neutral-900">
            with AEO Grader →
          </a>
        </p>
      </div>
    </main>
  )
}
```

- [ ] **Step 3: Verify page loads at /agent-report**

Start the dev server if not already running:
```bash
cd frontend && npm run dev
```

Open `http://localhost:3000/agent-report` in a browser.

Expected: form renders with an input field, "Analyze" button, and the AEO Grader link. Submitting `stripe.com` should navigate to `/agent-report/stripe.com`.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/agent-report/page.tsx frontend/app/agent-report/AgentReportForm.tsx
git commit -m "feat(agent-report): landing page"
```

---

## Task 13: Results Page & Loading Skeleton

**Files:**
- Create: `frontend/app/agent-report/[domain]/page.tsx`
- Create: `frontend/app/agent-report/[domain]/loading.tsx`

- [ ] **Step 1: Create loading.tsx**

Create `frontend/app/agent-report/[domain]/loading.tsx`:
```tsx
export default function AgentReportLoading() {
  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <div className="h-48 animate-pulse rounded-2xl bg-neutral-100" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-neutral-100" />
        ))}
      </div>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-16 animate-pulse rounded-2xl bg-neutral-100" />
      ))}
    </main>
  )
}
```

- [ ] **Step 2: Create [domain]/page.tsx**

Create `frontend/app/agent-report/[domain]/page.tsx`:
```tsx
"use client"
import { use, useEffect, useRef, useState } from "react"
import type { AgentCheckResponse, SSEEvent } from "@/lib/agent-check/types"
import ScanProgress from "@/components/agent-report/ScanProgress"
import ReportLayout from "@/components/agent-report/ReportLayout"

interface Props {
  params: Promise<{ domain: string }>
}

export default function AgentReportDomainPage({ params }: Props) {
  const { domain } = use(params)
  const decodedDomain = decodeURIComponent(domain)

  const [completedBlocks, setCompletedBlocks] = useState<Set<string>>(new Set())
  const [result, setResult] = useState<AgentCheckResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const hasStarted = useRef(false)

  useEffect(() => {
    if (hasStarted.current) return
    hasStarted.current = true

    async function runScan() {
      try {
        const res = await fetch("/api/agent-check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: `https://${decodedDomain}` }),
        })

        if (!res.ok) {
          const data = await res.json().catch(() => ({})) as { error?: string }
          setError(data.error ?? `HTTP ${res.status}`)
          return
        }

        const reader = res.body?.getReader()
        if (!reader) { setError("No response stream"); return }

        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const chunks = buffer.split("\n\n")
          buffer = chunks.pop() ?? ""
          for (const chunk of chunks) {
            const line = chunk.trim()
            if (!line.startsWith("data: ")) continue
            try {
              const event = JSON.parse(line.slice(6)) as SSEEvent
              if (event.type === "block") {
                setCompletedBlocks(prev => new Set([...prev, event.block]))
              } else if (event.type === "complete") {
                setResult(event.result)
              } else if (event.type === "error") {
                setError(event.message)
              }
            } catch { /* malformed line, skip */ }
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Scan failed")
      }
    }

    runScan()
  }, [decodedDomain])

  if (error) {
    return (
      <main className="mx-auto max-w-3xl p-8">
        <p className="text-red-600">{error}</p>
        <a href="/agent-report" className="mt-4 inline-block text-sm underline hover:text-neutral-900">
          Try another site
        </a>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-3xl p-8">
      {result
        ? <ReportLayout result={result} />
        : <ScanProgress domain={decodedDomain} completedBlocks={completedBlocks} />
      }
    </main>
  )
}
```

- [ ] **Step 3: End-to-end smoke test**

With the dev server running, open `http://localhost:3000/agent-report`, enter `github.com`, click Analyze.

Expected:
- Navigates to `/agent-report/github.com`
- Shows "Scanning github.com…" with steps activating one by one over ~15–30 seconds
- After all 4 blocks complete, shows the full report with score, grade badge, 4 block cards, and 3 accordion sections

- [ ] **Step 4: Test calibration — run 3 scans**

In the browser (or via curl), scan:
- `stripe.com` — expected ~50–80/100 (has OpenAPI, good API key docs, OAuth)
- `github.com` — expected ~40–65/100
- `notion.so` — expected ~30–55/100

If all three return 0 or 100, there is a bug in the check logic. Debug by logging intermediate `checks` objects in the API route.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/agent-report/[domain]/page.tsx frontend/app/agent-report/[domain]/loading.tsx
git commit -m "feat(agent-report): results page with SSE streaming + loading skeleton"
```

---

## Task 14: Playwright Service Skeleton

**Files:**
- Create: `playwright-service/src/types.ts`
- Create: `playwright-service/src/index.ts`
- Create: `playwright-service/package.json`
- Create: `playwright-service/tsconfig.json`
- Create: `playwright-service/Dockerfile`
- Create: `playwright-service/README.md`
- Create: `playwright-service/.env.example`

- [ ] **Step 1: Create playwright-service/src/types.ts**

Create `playwright-service/src/types.ts`:
```typescript
interface CheckResult {
  score: number
  maxScore: number
  found: boolean
}

export interface BrowserOperabilityResult {
  status: "complete"
  score: number
  maxScore: number
  checks: {
    semanticHtml:       CheckResult
    ariaAttributes:     CheckResult
    stableUrls:         CheckResult
    keyboardNavigation: CheckResult
    noCaptcha:          CheckResult
  }
}

export interface ScanRequest {
  url: string
}
```

- [ ] **Step 2: Create playwright-service/src/index.ts**

Create `playwright-service/src/index.ts`:
```typescript
import express from "express"
import type { BrowserOperabilityResult, ScanRequest } from "./types"

const app = express()
app.use(express.json())

const MOCK_RESULT: BrowserOperabilityResult = {
  status: "complete",
  score: 0,
  maxScore: 25,
  checks: {
    semanticHtml:       { score: 0, maxScore: 7, found: false },
    ariaAttributes:     { score: 0, maxScore: 5, found: false },
    stableUrls:         { score: 0, maxScore: 5, found: false },
    keyboardNavigation: { score: 0, maxScore: 4, found: false },
    noCaptcha:          { score: 0, maxScore: 4, found: false },
  },
}

app.post("/scan", (req, res) => {
  const { url } = req.body as ScanRequest
  if (!url || typeof url !== "string") {
    res.status(400).json({ error: "url is required" })
    return
  }
  console.log(`[mock] scan requested for: ${url}`)
  res.json(MOCK_RESULT)
})

app.get("/health", (_req, res) => {
  res.json({ status: "ok" })
})

const port = process.env.PORT ?? 3001
app.listen(port, () => {
  console.log(`Playwright service listening on port ${port}`)
})
```

- [ ] **Step 3: Create playwright-service/package.json**

Create `playwright-service/package.json`:
```json
{
  "name": "playwright-service",
  "version": "0.1.0",
  "private": true,
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts"
  },
  "dependencies": {
    "express": "^4.18.2"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/node": "^22",
    "ts-node": "^10.9.2",
    "typescript": "^5"
  }
}
```

- [ ] **Step 4: Create playwright-service/tsconfig.json**

Create `playwright-service/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "dist",
    "rootDir": "src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
```

- [ ] **Step 5: Create playwright-service/Dockerfile**

Create `playwright-service/Dockerfile`:
```dockerfile
FROM node:20-slim

WORKDIR /app

COPY package*.json ./
RUN npm ci --omit=dev

COPY dist ./dist

EXPOSE 3001

CMD ["node", "dist/index.js"]
```

- [ ] **Step 6: Create playwright-service/.env.example**

Create `playwright-service/.env.example`:
```
PORT=3001
```

- [ ] **Step 7: Create playwright-service/README.md**

Create `playwright-service/README.md`:
```markdown
# Playwright Service

Express server that provides browser-based operability checks for the Agent Operability Report.

## Current status

**MVP: mock only.** All check endpoints return score 0 with `status: "complete"`.
Real Playwright logic will be added in V1.0.

## API

### POST /scan

Request:
```json
{ "url": "https://example.com" }
```

Response (mock):
```json
{
  "status": "complete",
  "score": 0,
  "maxScore": 25,
  "checks": {
    "semanticHtml":       { "score": 0, "maxScore": 7, "found": false },
    "ariaAttributes":     { "score": 0, "maxScore": 5, "found": false },
    "stableUrls":         { "score": 0, "maxScore": 5, "found": false },
    "keyboardNavigation": { "score": 0, "maxScore": 4, "found": false },
    "noCaptcha":          { "score": 0, "maxScore": 4, "found": false }
  }
}
```

### GET /health

Returns `{ "status": "ok" }`.

## Local dev

```bash
npm install
npm run dev
```

## Docker

Build: `docker build -t playwright-service .`
Run: `docker run -p 3001:3001 playwright-service`

## Implementing real checks (V1.0)

Replace the `MOCK_RESULT` in `src/index.ts` with actual Playwright logic per check:
- `semanticHtml` — count semantic landmark elements (`<main>`, `<nav>`, `<article>`, etc.)
- `ariaAttributes` — count elements with `role` / `aria-*` attributes
- `stableUrls` — check for hash-only navigation vs real URL changes
- `keyboardNavigation` — tab through page, verify focus indicators
- `noCaptcha` — detect CAPTCHA widgets by selector / network request pattern
```

- [ ] **Step 8: Install dependencies and verify service starts**

```bash
cd playwright-service && npm install && npm run dev
```

Expected output: `Playwright service listening on port 3001`

In another terminal:
```bash
curl -X POST http://localhost:3001/scan \
  -H "Content-Type: application/json" \
  -d '{"url":"https://stripe.com"}'
```

Expected: JSON with `status: "complete"` and all scores at 0.

- [ ] **Step 9: Commit**

```bash
git add playwright-service/
git commit -m "feat: Playwright service skeleton — mock POST /scan endpoint"
```

---

## Task 15: Infrastructure Updates

**Files:**
- Modify: `docker-compose.yml`
- Create/Modify: `frontend/.env.example`

- [ ] **Step 1: Read current docker-compose.yml**

Open `docker-compose.yml` at the project root and note its current content before editing.

- [ ] **Step 2: Add playwright service to docker-compose.yml**

Add the `playwright` service and update the `frontend` service environment. The final relevant section of `docker-compose.yml` should look like this (merge with existing content — don't replace the whole file):

In the `services:` block, add:
```yaml
  playwright:
    build:
      context: ./playwright-service
      dockerfile: Dockerfile
    ports:
      - "3001:3001"
    environment:
      PORT: 3001
    restart: unless-stopped
```

In the existing `frontend:` service, add to `environment:`:
```yaml
      PLAYWRIGHT_SERVICE_URL: http://playwright:3001
      NEXT_PUBLIC_SITE_URL: http://localhost:3000
```

- [ ] **Step 3: Create frontend/.env.example**

If `frontend/.env.example` does not already exist, create it. If it does exist, append the following lines:

```
# Agent Operability Report
PLAYWRIGHT_SERVICE_URL=        # http://playwright:3001 in Docker; leave blank to use mock
NEXT_PUBLIC_SITE_URL=          # https://your-domain.com — used in AgentReadinessBot User-Agent
```

- [ ] **Step 4: Verify docker-compose build**

```bash
docker-compose build playwright
```

Expected: build completes without errors.

- [ ] **Step 5: Run full stack and verify integration**

```bash
docker-compose up frontend playwright
```

Open `http://localhost:3000/agent-report` and scan `linear.app`.

Expected: scan completes, Block 2 shows "Coming soon", all other blocks show real scores.

- [ ] **Step 6: Commit**

```bash
git add docker-compose.yml frontend/.env.example
git commit -m "feat: add playwright service to docker-compose; add env vars"
```

---

## Self-Review Notes

### Spec coverage check

| Spec section | Task |
|---|---|
| Block 1 — MCP, OpenAPI, Coverage, Public API | Task 5 |
| Block 2 — stub + full types | Task 6 |
| Block 3 — llms.txt, robots, schema.org, SDK | Task 7 |
| Block 4 — OAuth, API keys, CORS | Task 8 |
| Grade thresholds (0–25/26–50/51–75/76–90/91–100) | Task 4 |
| SSE event protocol | Task 9 + 10 |
| Rate limit (10/IP/hour, HTTP 429) | Task 10 (route.ts) |
| 30s global timeout | Task 9 (orchestrator) |
| 8s per-check timeout | Tasks 5–8 (fetchWithTimeout default) |
| User-Agent header | Tasks 5, 7, 8 (NEXT_PUBLIC_SITE_URL) |
| Re-scan on every page load | Task 13 |
| SSE streaming (fetch + ReadableStream) | Task 10 + 13 |
| Loading skeleton | Task 13 |
| Landing page /agent-report | Task 12 |
| Results page /agent-report/[domain] | Task 13 |
| Share footer (copy link, scan another, AEO link) | Task 11 (ReportLayout) |
| Playwright service skeleton + POST /scan | Task 14 |
| callBrowserService via PLAYWRIGHT_SERVICE_URL | Task 6 |
| docker-compose playwright service | Task 15 |
| .env.example additions | Task 15 |
| TypeScript strict, no any | All tasks |
