# Sonnet Router + Page Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace hardcoded page paths in Phase 2 Haiku agents with a Sonnet-powered router that discovers real pages from the site's nav/sitemap and injects platform-specific task hints, so checks like SDK Docs and Schema.org find evidence that currently scores 0.

**Architecture:** Insert a "Phase 1.5" step between Phase 1 (deterministic) and Phase 2 (Haiku agents). Phase 1.5 deterministically extracts nav links + sitemap candidates from the already-fetched homepage HTML, then makes one Sonnet call to map the best 3 URLs per check type (using world knowledge to supplement discovery) and produce task hints. Phase 2 agents receive pre-fetched page content + hints instead of fetching hardcoded paths themselves.

**Tech Stack:** TypeScript, Vitest, Next.js (existing stack). OpenRouter for Sonnet (`anthropic/claude-sonnet-4-5`) and Haiku (`anthropic/claude-haiku-4-5`) calls via the existing `callOpenRouter` util.

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/lib/agent-check/types.ts` | Modify | Add `RouterOutput`, `RouterPageMap`, `RouterHintMap` types |
| `frontend/lib/agent-check/page-router.ts` | **Create** | Nav extraction, sitemap fetch, candidate building, Sonnet router call, page fetching |
| `frontend/lib/agent-check/__tests__/page-router.test.ts` | **Create** | Tests for nav extraction and router orchestration |
| `frontend/lib/agent-check/phase2-agents.ts` | Modify | Agents accept `(domain, pages, taskHint)` instead of fetching their own pages |
| `frontend/lib/agent-check/__tests__/phase2-agents.test.ts` | Modify | Update call signatures, remove fetch mocking (agents no longer fetch) |
| `frontend/lib/agent-check/index.ts` | Modify | Call `runPageRouter` between Phase 1 and Phase 2; update `runPhase2` signature |

---

## Task 1: Add RouterOutput types to types.ts

**Files:**
- Modify: `frontend/lib/agent-check/types.ts`

- [ ] **Step 1: Add types after the Phase 2 section**

Open `frontend/lib/agent-check/types.ts`. After the `Phase2CheckName` type (currently around line 96), add:

```typescript
// ── Page Router ───────────────────────────────────────────────────────────────

export type RouterPageMap = Partial<Record<Phase2CheckName, string>>
export type RouterHintMap = Partial<Record<Phase2CheckName, string>>

export interface RouterOutput {
  platformHint: string
  pages: RouterPageMap      // pre-fetched HTML content per check type
  taskHints: RouterHintMap  // one-line platform-specific hint per check type
}
```

- [ ] **Step 2: Verify it compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/lib/agent-check/types.ts
git commit -m "feat: add RouterOutput types for page router"
```

---

## Task 2: Create page-router.ts — nav extraction, sitemap, page fetching

**Files:**
- Create: `frontend/lib/agent-check/page-router.ts`
- Create: `frontend/lib/agent-check/__tests__/page-router.test.ts`

- [ ] **Step 1: Write failing tests for extractNavLinks**

Create `frontend/lib/agent-check/__tests__/page-router.test.ts`:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { extractNavLinks, buildCandidates } from "../page-router"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function notFound(): Response { return new Response("Not Found", { status: 404 }) }
function okText(body: string): Response { return new Response(body, { status: 200 }) }

beforeEach(() => { mockFetch.mockReset() })

describe("extractNavLinks", () => {
  it("extracts links from nav elements", () => {
    const html = `<nav><a href="/docs">Docs</a><a href="/api">API</a></nav>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).toContain("https://example.com/docs")
    expect(result).toContain("https://example.com/api")
  })

  it("includes doc subdomain links from nav", () => {
    const html = `<nav><a href="https://docs.example.com/sdk">SDK</a></nav>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).toContain("https://docs.example.com/sdk")
  })

  it("excludes external unrelated domains", () => {
    const html = `<nav><a href="https://twitter.com/example">Twitter</a></nav>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).not.toContain("https://twitter.com/example")
  })

  it("picks up keyword-bearing links outside structural elements", () => {
    const html = `<div><a href="/developers/sdk">SDK</a></div>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).toContain("https://example.com/developers/sdk")
  })

  it("ignores hash and query-only hrefs", () => {
    const html = `<nav><a href="#section">Section</a><a href="?tab=1">Tab</a></nav>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).toHaveLength(0)
  })
})

describe("buildCandidates", () => {
  it("merges nav links and sitemap candidates, capped at 35", async () => {
    const html = `<nav><a href="/docs">Docs</a></nav>`
    mockFetch
      .mockResolvedValueOnce(okText("Sitemap: https://example.com/sitemap.xml"))
      .mockResolvedValueOnce(okText(`
        <urlset>
          <url><loc>https://example.com/api/reference</loc></url>
          <url><loc>https://example.com/developers</loc></url>
        </urlset>
      `))
    const result = await buildCandidates(html, "https://example.com")
    expect(result).toContain("https://example.com/docs")
    expect(result).toContain("https://example.com/api/reference")
    expect(result.length).toBeLessThanOrEqual(35)
  })

  it("adds fallback paths when nav yields fewer than 3 links", async () => {
    const html = `<html></html>`
    mockFetch.mockResolvedValue(notFound())
    const result = await buildCandidates(html, "https://example.com")
    expect(result).toContain("https://example.com/docs")
  })

  it("deduplicates URLs across nav and sitemap", async () => {
    const html = `<nav><a href="/docs">Docs</a></nav>`
    mockFetch
      .mockResolvedValueOnce(okText("Sitemap: https://example.com/sitemap.xml"))
      .mockResolvedValueOnce(okText(`<urlset><url><loc>https://example.com/docs</loc></url></urlset>`))
    const result = await buildCandidates(html, "https://example.com")
    expect(result.filter(u => u === "https://example.com/docs")).toHaveLength(1)
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npx vitest run lib/agent-check/__tests__/page-router.test.ts
```

Expected: FAIL — `extractNavLinks` not found.

- [ ] **Step 3: Create page-router.ts with nav extraction, sitemap, and page fetching**

Create `frontend/lib/agent-check/page-router.ts`:

```typescript
import { fetchWithTimeout } from "./utils"
import type { Phase2CheckName, RouterOutput } from "./types"

const HEADERS = { "User-Agent": `AgentReadinessBot/1.0` }
const DOC_SUBDOMAIN = /^https?:\/\/(docs|developer|api|dev)\./
const KEYWORD_HREF = /docs|api|developer|sdk|library|reference/i
const SITEMAP_KEYWORD = /doc|api|sdk|developer|reference/i
const FALLBACK_PATHS = ["/docs", "/developers", "/api", "/about"]

const HARDCODED_PATHS: Record<Phase2CheckName, string[]> = {
  mcpServer:        ["/developers", "/docs", "/platform"],
  openApiSpec:      ["/developers", "/docs", "/api", "/platform", "/build"],
  publicApiExists:  ["/developers", "/docs"],
  schemaOrg:        ["/about", "/product", "/features", "/platform"],
  sdkDocs:          ["/developers", "/docs", "/build", "/platform"],
  oauth:            ["/docs/authentication", "/docs/auth", "/developers", "/security"],
  apiKeySupport:    ["/docs/authentication", "/developers", "/api"],
}

function resolveHref(href: string, baseUrl: string): string | null {
  try { return new URL(href, baseUrl).href } catch { return null }
}

function isSameDomainOrDocSubdomain(href: string, hostname: string): boolean {
  try {
    const u = new URL(href)
    const base = hostname.replace(/^www\./, "")
    if (u.hostname === hostname || u.hostname === `www.${base}` || u.hostname === base) return true
    if (u.hostname.endsWith(`.${base}`) && DOC_SUBDOMAIN.test(href)) return true
    return false
  } catch { return false }
}

export function extractNavLinks(html: string, baseUrl: string): string[] {
  const hostname = new URL(baseUrl).hostname
  const candidates = new Set<string>()

  // Links inside structural elements
  const structureRe = /<(?:nav|header|footer)[^>]*>([\s\S]*?)<\/(?:nav|header|footer)>/gi
  let m: RegExpExecArray | null
  while ((m = structureRe.exec(html)) !== null) {
    const block = m[1]
    const hrefRe = /href=["']([^"'#?][^"']*)["']/gi
    let h: RegExpExecArray | null
    while ((h = hrefRe.exec(block)) !== null) {
      const abs = resolveHref(h[1], baseUrl)
      if (abs && isSameDomainOrDocSubdomain(abs, hostname)) candidates.add(abs)
    }
  }

  // Keyword-bearing links anywhere in the page
  const allHrefRe = /href=["']([^"'#?][^"']*)["']/gi
  while ((m = allHrefRe.exec(html)) !== null) {
    if (!KEYWORD_HREF.test(m[1])) continue
    const abs = resolveHref(m[1], baseUrl)
    if (abs && isSameDomainOrDocSubdomain(abs, hostname)) candidates.add(abs)
  }

  return [...candidates].slice(0, 25)
}

async function fetchSitemapCandidates(baseUrl: string): Promise<string[]> {
  const candidates: string[] = []
  try {
    let sitemapUrl = `${baseUrl}/sitemap.xml`
    try {
      const robotsRes = await fetchWithTimeout(`${baseUrl}/robots.txt`, { headers: HEADERS }, 5000)
      if (robotsRes.ok) {
        const txt = await robotsRes.text()
        const match = /^Sitemap:\s*(.+)$/mi.exec(txt)
        if (match) sitemapUrl = match[1].trim()
      }
    } catch { /* use default sitemap URL */ }

    const sitemapRes = await fetchWithTimeout(sitemapUrl, { headers: HEADERS }, 5000)
    if (!sitemapRes.ok) return candidates
    const xml = await sitemapRes.text()
    const locRe = /<loc>([^<]+)<\/loc>/gi
    let m: RegExpExecArray | null
    while ((m = locRe.exec(xml)) !== null && candidates.length < 20) {
      const url = m[1].trim()
      if (SITEMAP_KEYWORD.test(url)) candidates.push(url)
    }
  } catch { /* sitemap unavailable */ }
  return candidates
}

export async function buildCandidates(html: string, baseUrl: string): Promise<string[]> {
  const [navLinks, sitemapLinks] = await Promise.all([
    Promise.resolve(extractNavLinks(html, baseUrl)),
    fetchSitemapCandidates(baseUrl),
  ])
  const seen = new Set<string>()
  const all: string[] = []
  for (const url of [...navLinks, ...sitemapLinks]) {
    if (!seen.has(url)) { seen.add(url); all.push(url) }
  }
  if (all.length < 3) {
    for (const path of FALLBACK_PATHS) {
      const url = new URL(path, baseUrl).href
      if (!seen.has(url)) { seen.add(url); all.push(url) }
    }
  }
  return all.slice(0, 35)
}

export async function fetchPagesForUrls(urls: string[]): Promise<string> {
  const parts: string[] = []
  for (const url of urls.slice(0, 3)) {
    try {
      const res = await fetchWithTimeout(url, { headers: HEADERS }, 8000)
      if (res.ok) {
        const text = await res.text()
        parts.push(`--- ${url} ---\n${text.slice(0, 2000)}`)
      }
    } catch { /* skip */ }
  }
  return parts.join("\n\n")
}

async function buildFallbackOutput(baseUrl: string, needed: Set<Phase2CheckName>): Promise<RouterOutput> {
  const entries = await Promise.all(
    [...needed].map(async name => {
      const urls = HARDCODED_PATHS[name].map(p => new URL(p, baseUrl).href)
      return [name, await fetchPagesForUrls(urls)] as [Phase2CheckName, string]
    })
  )
  return {
    platformHint: "",
    pages: Object.fromEntries(entries),
    taskHints: Object.fromEntries([...needed].map(n => [n, ""])),
  }
}

// callSonnetRouter and runPageRouter added in Task 3
export { buildFallbackOutput }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx vitest run lib/agent-check/__tests__/page-router.test.ts
```

Expected: all PASS.

- [ ] **Step 5: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/agent-check/page-router.ts frontend/lib/agent-check/__tests__/page-router.test.ts
git commit -m "feat: add nav/sitemap page discovery to page-router"
```

---

## Task 3: Add Sonnet router call and runPageRouter

**Files:**
- Modify: `frontend/lib/agent-check/page-router.ts`
- Modify: `frontend/lib/agent-check/__tests__/page-router.test.ts`

- [ ] **Step 1: Add failing tests for callSonnetRouter and runPageRouter**

Append to `frontend/lib/agent-check/__tests__/page-router.test.ts`:

```typescript
import { callSonnetRouter, runPageRouter } from "../page-router"
import * as utils from "../utils"

// callOpenRouter is already mocked via the vi.mock at the top of the file
const mockOpenRouter = vi.mocked(utils.callOpenRouter)

describe("callSonnetRouter", () => {
  it("returns parsed RouterOutput on valid Sonnet response", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      platformHint: "GitHub — code hosting",
      pages: {
        sdkDocs: ["https://docs.github.com/rest/overview/libraries"],
        schemaOrg: ["https://github.com/about"],
        mcpServer: [], openApiSpec: [], publicApiExists: [], oauth: [], apiKeySupport: [],
      },
      taskHints: {
        sdkDocs: "GitHub SDK is Octokit",
        schemaOrg: "",
        mcpServer: "", openApiSpec: "", publicApiExists: "", oauth: "", apiKeySupport: "",
      },
    }))
    const result = await callSonnetRouter("github.com", "GitHub", "Where the world builds software", ["https://github.com/about"])
    expect(result.platformHint).toBe("GitHub — code hosting")
    expect(result.pages.sdkDocs).toContain("https://docs.github.com/rest/overview/libraries")
    expect(result.taskHints.sdkDocs).toBe("GitHub SDK is Octokit")
  })

  it("throws on malformed JSON so runPageRouter can catch and fallback", async () => {
    mockOpenRouter.mockResolvedValue("not json {{{")
    await expect(callSonnetRouter("example.com", "", "", [])).rejects.toThrow()
  })
})

describe("runPageRouter", () => {
  it("fetches pages for needed checks using Sonnet-routed URLs", async () => {
    // Sonnet router returns a specific URL for sdkDocs
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      platformHint: "Example platform",
      pages: {
        sdkDocs: ["https://docs.example.com/sdk"],
        schemaOrg: ["https://example.com/about"],
        mcpServer: [], openApiSpec: [], publicApiExists: [], oauth: [], apiKeySupport: [],
      },
      taskHints: {
        sdkDocs: "Check for @example/sdk on npm",
        schemaOrg: "", mcpServer: "", openApiSpec: "", publicApiExists: "", oauth: "", apiKeySupport: "",
      },
    }))
    // Page fetches: robots.txt, sitemap (both 404), then the routed pages
    mockFetch
      .mockResolvedValueOnce(notFound())  // robots.txt
      .mockResolvedValueOnce(notFound())  // sitemap.xml
      .mockResolvedValueOnce(okText("npm install @example/sdk"))  // docs.example.com/sdk
      .mockResolvedValueOnce(okText('<script type="application/ld+json">{"@type":"SoftwareApplication"}</script>'))

    const needed = new Set<Phase2CheckName>(["sdkDocs", "schemaOrg"])
    const result = await runPageRouter("https://example.com", "example.com", "<nav><a href='/docs'>Docs</a></nav>", needed)

    expect(result.pages.sdkDocs).toContain("npm install @example/sdk")
    expect(result.taskHints.sdkDocs).toBe("Check for @example/sdk on npm")
  })

  it("falls back to hardcoded paths when Sonnet call fails", async () => {
    mockOpenRouter.mockRejectedValue(new Error("network error"))
    mockFetch
      .mockResolvedValueOnce(notFound())  // robots.txt
      .mockResolvedValueOnce(notFound())  // sitemap.xml
      .mockResolvedValue(okText("fallback content"))  // hardcoded path fetches

    const needed = new Set<Phase2CheckName>(["sdkDocs"])
    const result = await runPageRouter("https://example.com", "example.com", "", needed)

    expect(result.platformHint).toBe("")
    expect(result.pages.sdkDocs).toContain("fallback content")
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npx vitest run lib/agent-check/__tests__/page-router.test.ts
```

Expected: FAIL — `callSonnetRouter` and `runPageRouter` not exported.

- [ ] **Step 3: Add callSonnetRouter and runPageRouter to page-router.ts**

Replace the last two lines of `page-router.ts` (the `export { buildFallbackOutput }` line) with:

```typescript
import { callOpenRouter } from "./utils"

const SONNET = "anthropic/claude-sonnet-4-5"

interface SonnetRouterRaw {
  platformHint: string
  pages: Partial<Record<Phase2CheckName, string[]>>
  taskHints: Partial<Record<Phase2CheckName, string>>
}

function buildRouterPrompt(domain: string, title: string, description: string, candidates: string[]): string {
  return `You are a routing agent for an AI agent operability checker. Your job is to identify the best pages to fetch for each check type.

DOMAIN: ${domain}
PAGE TITLE: ${title}
META DESCRIPTION: ${description}

DISCOVERED CANDIDATE URLs:
${candidates.map((u, i) => `${i + 1}. ${u}`).join("\n")}

For each check type, return the 3 best URLs to fetch. You may use URLs from the candidate list OR URLs from your world knowledge if the candidate list is missing something important. Also return a one-line task hint if you have specific knowledge about this platform.

Check types:
- mcpServer: find an official MCP (Model Context Protocol) server
- openApiSpec: find an OpenAPI/Swagger machine-readable spec file
- publicApiExists: find the developer portal or API documentation
- schemaOrg: find pages with JSON-LD structured data
- sdkDocs: find SDK / client library documentation
- oauth: find OAuth 2.0 authentication documentation
- apiKeySupport: find API key / personal access token documentation

Return ONLY valid JSON (no markdown, no other text):
{
  "platformHint": "one-line platform description or empty string",
  "pages": {
    "mcpServer": ["url1", "url2", "url3"],
    "openApiSpec": ["url1", "url2", "url3"],
    "publicApiExists": ["url1", "url2", "url3"],
    "schemaOrg": ["url1", "url2", "url3"],
    "sdkDocs": ["url1", "url2", "url3"],
    "oauth": ["url1", "url2", "url3"],
    "apiKeySupport": ["url1", "url2", "url3"]
  },
  "taskHints": {
    "mcpServer": "specific hint or empty string",
    "openApiSpec": "specific hint or empty string",
    "publicApiExists": "specific hint or empty string",
    "schemaOrg": "specific hint or empty string",
    "sdkDocs": "specific hint or empty string",
    "oauth": "specific hint or empty string",
    "apiKeySupport": "specific hint or empty string"
  }
}`
}

export async function callSonnetRouter(
  domain: string,
  title: string,
  description: string,
  candidates: string[]
): Promise<SonnetRouterRaw> {
  const prompt = buildRouterPrompt(domain, title, description, candidates)
  const raw = await callOpenRouter(SONNET, prompt, 1000)
  const content = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim()
  const parsed = JSON.parse(content) as SonnetRouterRaw
  if (!parsed?.pages || typeof parsed.pages !== "object") throw new Error("Invalid router response")
  return parsed
}

export async function runPageRouter(
  url: string,
  domain: string,
  homepageHtml: string,
  needed: Set<Phase2CheckName>
): Promise<RouterOutput> {
  if (needed.size === 0) return { platformHint: "", pages: {}, taskHints: {} }

  try {
    const candidates = await buildCandidates(homepageHtml, url)
    const title = /<title[^>]*>([^<]*)<\/title>/i.exec(homepageHtml)?.[1]?.trim() ?? ""
    const metaDesc = /<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)["']/i.exec(homepageHtml)?.[1]?.trim() ?? ""

    const routerResult = await callSonnetRouter(domain, title, metaDesc, candidates)

    const pageEntries = await Promise.all(
      [...needed].map(async name => {
        const urls = routerResult.pages[name] ?? []
        return [name, await fetchPagesForUrls(urls)] as [Phase2CheckName, string]
      })
    )

    return {
      platformHint: routerResult.platformHint ?? "",
      pages: Object.fromEntries(pageEntries),
      taskHints: routerResult.taskHints ?? {},
    }
  } catch {
    return buildFallbackOutput(url, needed)
  }
}

export { buildFallbackOutput }
```

> **Note:** The `import { callOpenRouter }` line at the top should be merged with the existing `import { fetchWithTimeout } from "./utils"` line at the top of the file, making it `import { fetchWithTimeout, callOpenRouter } from "./utils"`. Also add `import type { RouterOutput } from "./types"` to the existing type imports.

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx vitest run lib/agent-check/__tests__/page-router.test.ts
```

Expected: all PASS.

- [ ] **Step 5: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/agent-check/page-router.ts frontend/lib/agent-check/__tests__/page-router.test.ts
git commit -m "feat: add Sonnet router call and runPageRouter orchestrator"
```

---

## Task 4: Update phase2-agents.ts — agents accept pre-fetched pages

**Files:**
- Modify: `frontend/lib/agent-check/phase2-agents.ts`
- Modify: `frontend/lib/agent-check/__tests__/phase2-agents.test.ts`

- [ ] **Step 1: Update the existing phase2-agents tests**

Replace the entire content of `frontend/lib/agent-check/__tests__/phase2-agents.test.ts` with:

```typescript
import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkMcpServerAgent, checkOpenApiSpecAgent, checkOAuthAgent } from "../phase2-agents"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, callOpenRouter: vi.fn() }
})

const mockOpenRouter = vi.mocked(utils.callOpenRouter)

beforeEach(() => { mockOpenRouter.mockReset() })

const PAGES = "--- /docs ---\n<html>some page content</html>"

describe("checkMcpServerAgent", () => {
  it("returns found=true when Haiku identifies an MCP repo", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: true,
      confidence: "high",
      evidence: "https://github.com/example/mcp-server",
      details: "Official MCP server repository",
    }))
    const result = await checkMcpServerAgent("example.com", PAGES, "")
    expect(result.found).toBe(true)
    expect(result.confidence).toBe("high")
    expect(result.evidence).toContain("github.com")
  })

  it("returns found=false when Haiku finds nothing", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: false,
      confidence: "high",
      evidence: "",
    }))
    const result = await checkMcpServerAgent("example.com", PAGES, "")
    expect(result.found).toBe(false)
  })

  it("returns safe fallback on OpenRouter error", async () => {
    mockOpenRouter.mockRejectedValue(new Error("timeout"))
    const result = await checkMcpServerAgent("example.com", PAGES, "")
    expect(result.found).toBe(false)
    expect(result.confidence).toBe("low")
  })

  it("injects task hint into the prompt sent to Haiku", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({ found: false, confidence: "low", evidence: "" }))
    await checkMcpServerAgent("example.com", PAGES, "Check github.com/example/mcp for the server")
    const calledPrompt = mockOpenRouter.mock.calls[0][1] as string
    expect(calledPrompt).toContain("Check github.com/example/mcp for the server")
  })
})

describe("checkOpenApiSpecAgent", () => {
  it("returns found=true when Haiku finds a spec URL in pre-fetched pages", async () => {
    const pages = "--- /api ---\n<a href='/api/spec.json'>OpenAPI</a>"
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: true,
      confidence: "high",
      evidence: "https://example.com/api/spec.json",
    }))
    const result = await checkOpenApiSpecAgent("example.com", pages, "")
    expect(result.found).toBe(true)
    expect(result.evidence).toContain("spec.json")
  })
})

describe("checkOAuthAgent", () => {
  it("returns found=false with safe fallback on JSON parse error", async () => {
    mockOpenRouter.mockResolvedValue("not valid json at all {{{")
    const result = await checkOAuthAgent("example.com", PAGES, "")
    expect(result.found).toBe(false)
    expect(result.confidence).toBe("low")
  })
})
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
cd frontend && npx vitest run lib/agent-check/__tests__/phase2-agents.test.ts
```

Expected: FAIL — current agents have signature `(url, homepageHtml)`, not `(domain, pages, taskHint)`.

- [ ] **Step 3: Rewrite phase2-agents.ts with new signatures**

Replace the entire content of `frontend/lib/agent-check/phase2-agents.ts` with:

```typescript
import { callOpenRouter } from "./utils"
import type { SubAgentResult } from "./types"

const HAIKU = "anthropic/claude-haiku-4-5"
const FALLBACK: SubAgentResult = { found: false, confidence: "low", evidence: "sub-agent error" }

function buildPrompt(domain: string, pages: string, task: string, taskHint: string): string {
  return `You are analyzing ${domain} for AI agent operability.

${pages ? `PAGES:\n${pages}` : "No pages available."}

TASK: ${task}${taskHint ? `\n\nPLATFORM HINT: ${taskHint}` : ""}

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
    const raw = await callOpenRouter(HAIKU, prompt, 400)
    const content = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim()
    const parsed = JSON.parse(content) as SubAgentResult
    if (typeof parsed.found !== "boolean" || !["high", "medium", "low"].includes(parsed.confidence)) {
      return FALLBACK
    }
    return parsed
  } catch { return FALLBACK }
}

export async function checkMcpServerAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Search for an official MCP (Model Context Protocol) server for ${domain}. Look for:
- Links or mentions of "MCP server", "model context protocol"
- A GitHub repository with "mcp" in the name alongside ${domain}
- Install instructions like "npx @modelcontextprotocol/" or similar
- Any reference to serving MCP protocol
Return the repository URL or install command as evidence.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkOpenApiSpecAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Find an OpenAPI or Swagger API specification for ${domain}. It may be linked from the pages provided. Look for:
- Links containing "openapi", "swagger", "api-spec", "api-docs", or "rest-api"
- File extensions .json or .yaml on spec-like paths
- Mentions of a machine-readable API specification URL
Return the direct URL to the spec file.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkPublicApiAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Determine if ${domain} offers a public API for programmatic access. Look in navigation, footer, and the pages provided for mentions of "API", "REST API", "GraphQL API", "developer platform", or links to API documentation. Return a URL to the API docs or developer portal.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkOAuthAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Find evidence that ${domain} supports OAuth 2.0 authentication. Look for text mentioning "OAuth 2.0", "OAuth2", "OpenID Connect", "authorization flow", or "access token" in the pages provided. Return a URL and a short quoted snippet as evidence.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkApiKeyAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Find evidence that ${domain} offers API keys or tokens for programmatic access. Look for "API key", "API token", "personal access token", "secret key", or "bearer token" in the pages provided. Return a URL and a short quoted snippet.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkSdkDocsAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Find evidence of a developer SDK for ${domain}. Look for links to npmjs.com, pypi.org, or GitHub alongside the word "SDK", or text like "npm install", "pip install", "client library" in the pages provided. Return the URL and package name if found.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkSchemaOrgAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Check the pages provided for JSON-LD structured data (inside <script type="application/ld+json"> tags). Look for @type values: SoftwareApplication, WebAPI, APIReference, Service, Action, or EntryPoint. Return the @type found and the page URL.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd frontend && npx vitest run lib/agent-check/__tests__/phase2-agents.test.ts
```

Expected: all PASS.

- [ ] **Step 5: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors (index.ts will break until Task 5 — that's expected at this point).

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/agent-check/phase2-agents.ts frontend/lib/agent-check/__tests__/phase2-agents.test.ts
git commit -m "feat: phase2 agents accept pre-fetched pages and task hints"
```

---

## Task 5: Wire Phase 1.5 in index.ts

**Files:**
- Modify: `frontend/lib/agent-check/index.ts`

- [ ] **Step 1: Add the import for runPageRouter**

At the top of `frontend/lib/agent-check/index.ts`, add to the existing imports:

```typescript
import { runPageRouter } from "./page-router"
import type { RouterOutput } from "./types"
```

- [ ] **Step 2: Update runPhase2 signature and body**

Replace the entire `runPhase2` function (lines 36–59 in the current file) with:

```typescript
async function runPhase2(
  domain: string,
  needed: Set<Phase2CheckName>,
  router: RouterOutput
): Promise<Partial<Record<Phase2CheckName, SubAgentResult>>> {
  if (needed.size === 0) return {}

  const hint = (n: Phase2CheckName) => router.taskHints[n] ?? ""
  const pages = (n: Phase2CheckName) => router.pages[n] ?? ""

  const tasks: Array<[Phase2CheckName, Promise<SubAgentResult>]> = []
  if (needed.has("mcpServer"))        tasks.push(["mcpServer",        checkMcpServerAgent(domain,        pages("mcpServer"),        hint("mcpServer"))])
  if (needed.has("openApiSpec"))      tasks.push(["openApiSpec",      checkOpenApiSpecAgent(domain,      pages("openApiSpec"),      hint("openApiSpec"))])
  if (needed.has("publicApiExists"))  tasks.push(["publicApiExists",  checkPublicApiAgent(domain,        pages("publicApiExists"),  hint("publicApiExists"))])
  if (needed.has("schemaOrg"))        tasks.push(["schemaOrg",        checkSchemaOrgAgent(domain,        pages("schemaOrg"),        hint("schemaOrg"))])
  if (needed.has("sdkDocs"))          tasks.push(["sdkDocs",          checkSdkDocsAgent(domain,          pages("sdkDocs"),          hint("sdkDocs"))])
  if (needed.has("oauth"))            tasks.push(["oauth",            checkOAuthAgent(domain,            pages("oauth"),            hint("oauth"))])
  if (needed.has("apiKeySupport"))    tasks.push(["apiKeySupport",    checkApiKeyAgent(domain,           pages("apiKeySupport"),    hint("apiKeySupport"))])

  const results = await Promise.allSettled(tasks.map(([, p]) => p))
  const merged: Partial<Record<Phase2CheckName, SubAgentResult>> = {}
  tasks.forEach(([name], i) => {
    const r = results[i]
    if (r.status === "fulfilled") merged[name] = r.value
  })
  return merged
}
```

- [ ] **Step 3: Insert Phase 1.5 in runScan**

In the `runScan` function, find this block (around line 159–161 in the current file):

```typescript
    // Phase 2 — Haiku sub-agents for unresolved checks
    const phase2Needed = identifyPhase2Checks(machine, discovery, auth)
    const phase2Results = await runPhase2(url, homepageHtml, phase2Needed)
```

Replace it with:

```typescript
    // Phase 2 — identify what needs agent resolution
    const phase2Needed = identifyPhase2Checks(machine, discovery, auth)

    // Phase 1.5 — Sonnet Router: discover real pages + inject platform hints
    const routerOutput = await runPageRouter(url, domain, homepageHtml, phase2Needed)

    // Phase 2 — Haiku sub-agents using router-provided pages and hints
    const phase2Results = await runPhase2(domain, phase2Needed, routerOutput)
```

- [ ] **Step 4: Run all tests**

```bash
cd frontend && npx vitest run
```

Expected: all PASS.

- [ ] **Step 5: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/lib/agent-check/index.ts
git commit -m "feat: wire Sonnet router as Phase 1.5 between deterministic checks and Haiku agents"
```

---

## Self-Review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Nav/header/footer link extraction | Task 2 — `extractNavLinks` |
| Sitemap candidate discovery | Task 2 — `fetchSitemapCandidates` |
| Doc subdomain filtering (docs.*, developer.*) | Task 2 — `isSameDomainOrDocSubdomain` |
| Fallback paths when nav is sparse | Task 2 — `buildCandidates` |
| Sonnet router call with world knowledge | Task 3 — `callSonnetRouter` |
| Platform hints injected into Haiku prompts | Tasks 3+4 — `buildPrompt` includes hint |
| Pre-fetched pages replace hardcoded paths | Task 4 — agent signatures |
| Fallback to hardcoded paths on Sonnet failure | Task 3 — `buildFallbackOutput` |
| Phase 1.5 runs only for unresolved checks | Task 5 — `needed` set passed to `runPageRouter` |
| No changes to Phase 1, sonnet-scoring, UI | No tasks touch those files ✓ |

**Placeholder scan:** No TBDs, TODOs, or vague steps found.

**Type consistency check:** `RouterOutput.pages` is `Partial<Record<Phase2CheckName, string>>` (HTML strings) throughout Tasks 1–5. `taskHints` is `Partial<Record<Phase2CheckName, string>>` throughout. Agent signatures are `(domain: string, pages: string, taskHint: string)` consistently across Tasks 4 and 5.
