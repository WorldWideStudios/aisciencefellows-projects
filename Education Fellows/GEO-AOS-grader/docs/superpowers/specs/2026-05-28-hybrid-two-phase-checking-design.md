# Hybrid Two-Phase Checking — Design Spec

**Date:** 2026-05-28  
**Updated:** 2026-05-29 — Phase 1.5 Sonnet Router added  
**Feature:** Improved Agent Operability scoring via deterministic HTTP + agentic LLM fallback  
**Status:** Approved

---

## Problem

The current single-pass HTTP checker returns NOT_FOUND and scores 0 for checks where the signal exists but lives at a non-standard path. A platform's OAuth docs might be at `/docs/authentication` instead of `/.well-known/oauth-authorization-server`. Their OpenAPI spec might be at `/platform/api/spec.json`. SDK docs might live under `/build` instead of `/developers`. The result is inaccurate scores, especially for niche or unconventional platforms — which are the primary audience for this tool.

---

## Solution: Hybrid Two-Phase Architecture

A two-phase scan followed by a Sonnet synthesis step. Phase 1 is fast and free. Phase 2 is triggered only when Phase 1 comes up empty. Sonnet produces nuanced, auditable scores from all collected evidence.

---

## Phase 1 — Deterministic HTTP

**Timing:** ≤8s per check, all checks in parallel  
**Cost:** $0  
**LLM:** None

### Homepage Pre-fetch

Before Phase 1 checks run, the orchestrator fetches the homepage HTML **once** and stores it in a local variable. This HTML is passed to all Phase 1 parsers and all Phase 2 sub-agents. The homepage is never fetched more than once per scan.

### Check Outputs

Each check returns one of three statuses:

```typescript
type Phase1Status = "FOUND" | "NOT_FOUND" | "UNCERTAIN"

type Phase1Result = {
  status: Phase1Status
  evidence?: string       // URL, snippet, or structured data found
  rawData?: unknown       // e.g. parsed OpenAPI spec object
}
```

### Checks Covered in Phase 1

| Check | Method | UNCERTAIN trigger |
|---|---|---|
| MCP Server | Well-known paths + Smithery API + mcp.so API with hostname verification | Registry match with low confidence |
| OpenAPI Spec | 7 standard paths + `api.`, `developer.` subdomains | Spec found but no `paths` object |
| llms.txt | Fetch `/llms.txt` and parse | Never — binary |
| robots.txt AI permissions | Fetch + parse agent rules | Never — binary |
| Schema.org | Parse JSON-LD from homepage HTML | Never — but Phase 2 checks inner pages if NOT_FOUND |
| CORS | HTTP OPTIONS on detected API endpoint | No API endpoint found |
| Public API | Homepage HTML signals + robots.txt `/api/` mentions | Only 1 of 2 signals present |

---

## Phase 1.5 — Sonnet Router (added 2026-05-29)

**Timing:** ~3–6s (discovery + one Sonnet call + parallel page fetches)  
**Cost:** ~$0.003–0.005 (one Sonnet call, short input/output)  
**LLM:** `anthropic/claude-sonnet-4-5` via OpenRouter  
**File:** `lib/agent-check/page-router.ts`

### Why It Exists

Phase 2 Haiku agents originally fetched hardcoded paths (`/developers`, `/docs`, `/product`, etc.) that don't match most real platforms. GitHub's SDK docs are at `docs.github.com`; Stripe's auth docs are at `stripe.com/docs/api`. The agents had no way to know this, so they returned 0 for things that clearly exist.

Phase 1.5 solves this by discovering where a site's relevant content actually lives before handing off to Haiku agents.

### Trigger Condition

Runs after Phase 1, before Phase 2. Only runs if at least one check needs Phase 2 (i.e., the `needed` set is non-empty). If Phase 1 resolved everything, Phase 1.5 is skipped.

### Step A: Nav/Sitemap Discovery (deterministic, no LLM)

From the already-fetched homepage HTML:

1. Extract `<a href>` from `<nav>`, `<header>`, `<footer>` elements
2. Also scan full HTML for links containing keywords: `docs`, `api`, `developer`, `sdk`, `library`, `reference`
3. Resolve relative URLs to absolute; filter to same domain **+** doc subdomains (`docs.*`, `developer.*`, `api.*`, `dev.*`)
4. Cap at 25 candidates
5. Fetch `robots.txt` → find `Sitemap:` directive → fetch sitemap → extract up to 20 keyword-matching URLs
6. Deduplicate, cap at 35 candidates total
7. Fallback: if fewer than 3 candidates, add `/docs`, `/developers`, `/api`, `/about`

### Step B: Sonnet Router Call

**Input:** domain, homepage `<title>` + `<meta description>`, list of ~35 candidate URLs

**Sonnet's job:**
1. Identify the platform if known ("GitHub — code hosting platform")
2. For each of 7 check types, return the 3 best URLs to fetch — from the candidate list **or** from world knowledge if candidates are missing something important
3. Return a one-line task hint per check type when it has specific knowledge ("GitHub's SDK is Octokit, @octokit/core on npm")

**Output schema:**
```typescript
{
  platformHint: string
  pages: Partial<Record<Phase2CheckName, string[]>>   // 3 URLs per check
  taskHints: Partial<Record<Phase2CheckName, string>> // platform-specific hints
}
```

**Fallback:** If the Sonnet router call fails, `buildFallbackOutput` fetches the original hardcoded paths — behavior is identical to the pre-Phase-1.5 system.

### Step C: Page Fetching

For each check in the `needed` set, the router fetches its 3 assigned URLs in parallel and concatenates the HTML excerpts (2000 chars each) into a single `pages` string. All unsafe URLs (localhost, private IP ranges, non-http protocols) are filtered out before fetching (SSRF protection).

### Types Added

```typescript
type RouterPageMap = Partial<Record<Phase2CheckName, string>>  // pre-fetched HTML content
type RouterHintMap = Partial<Record<Phase2CheckName, string>>  // one-line platform hints

interface RouterOutput {
  platformHint: string
  pages: RouterPageMap
  taskHints: RouterHintMap
}
```

---

## Phase 2 — Haiku Sub-Agents

**Timing:** ≤15s per sub-agent, all triggered sub-agents in parallel  
**Cost:** ~$0.02–0.04 if several checks run  
**LLM:** `anthropic/claude-haiku-4-5` via OpenRouter

### Trigger Condition

After Phase 1 completes, the orchestrator inspects each check's status. Any check returning `NOT_FOUND` or `UNCERTAIN` gets a Haiku sub-agent launched for it. If Phase 1 returns `FOUND` for everything, Phase 2 is skipped entirely.

### Sub-Agent Interface

Each sub-agent is an exported async function in `lib/agent-check/phase2-agents.ts`. **Note: signatures changed in 2026-05-29 update — agents no longer fetch their own pages.**

```typescript
type SubAgentResult = {
  found: boolean
  confidence: "high" | "medium" | "low"
  evidence: string    // URL or quoted text snippet
  details?: string    // extra context (e.g. repo age, package name)
}

// New signatures (post Phase 1.5):
async function checkMcpServerAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult>
async function checkOpenApiSpecAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult>
async function checkPublicApiAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult>
async function checkOAuthAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult>
async function checkApiKeyAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult>
async function checkSdkDocsAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult>
async function checkSchemaOrgAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult>
```

`pages` is pre-fetched HTML content from Phase 1.5 (concatenated excerpts). `taskHint` is the platform-specific hint from the Sonnet router, injected as `PLATFORM HINT: …` at the end of the task prompt. Agents perform **no HTTP fetching** themselves.

### Sub-Agent Task Prompts

Prompts are sent with the pre-fetched `pages` content and optional `PLATFORM HINT` appended. The prompt structure is:

```
You are analyzing {domain} for AI agent operability.

PAGES:
{pages}

TASK: {task description}

PLATFORM HINT: {taskHint}   ← only included when non-empty
```

**MCP Server task:**  
"Search for an official MCP (Model Context Protocol) server for {domain}. Look for links or mentions of 'MCP server', 'model context protocol', a GitHub repository with 'mcp' in the name alongside {domain}, or install instructions like 'npx @modelcontextprotocol/'. Return the repository URL or install command as evidence."

**OpenAPI / Swagger Spec task:**  
"Find an OpenAPI or Swagger API specification for {domain}. Look for links containing 'openapi', 'swagger', 'api-spec', 'api-docs', or 'rest-api', file extensions .json or .yaml on spec-like paths, or mentions of a machine-readable API specification URL. Return the direct URL to the spec file."

**OAuth 2.0 task:**  
"Find evidence that {domain} supports OAuth 2.0 authentication. Look for text mentioning 'OAuth 2.0', 'OAuth2', 'OpenID Connect', 'authorization flow', or 'access token'. Return a URL and a short quoted snippet as evidence."

**API Key / Token Support task:**  
"Find evidence that {domain} offers API keys or tokens for programmatic access. Look for 'API key', 'API token', 'personal access token', 'secret key', or 'bearer token'. Return a URL and short quote."

**SDK Documentation task:**  
"Find evidence of a developer SDK for {domain}. Look for links to npmjs.com, pypi.org, or GitHub alongside the word 'SDK', or text like 'npm install', 'pip install', 'client library'. Return the URL and package name if found."

**Schema.org task:**  
"Check the pages provided for JSON-LD structured data (inside `<script type="application/ld+json">` tags). Look for @type values: SoftwareApplication, WebAPI, APIReference, Service, Action, or EntryPoint. Return the @type found and the page URL."

**Public API Exists task:**  
"Determine if {domain} offers a public API for programmatic access. Look in navigation, footer, and the pages provided for mentions of 'API', 'REST API', 'GraphQL API', 'developer platform', or links to API documentation. Return a URL to the API docs or developer portal."

### OpenRouter Call Pattern

```typescript
const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
  method: "POST",
  headers: {
    "Authorization": `Bearer ${process.env.OPENROUTER_API_KEY}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    model: "anthropic/claude-haiku-4-5",
    messages: [{ role: "user", content: taskPrompt }],
    max_tokens: 500,
    response_format: { type: "json_object" },
  }),
})
```

Each sub-agent function wraps this call, parses the JSON response into `SubAgentResult`, and catches errors to return `{ found: false, confidence: "low", evidence: "error" }`.

---

## Sonnet Synthesis — Final Scoring

**Timing:** ≤10s  
**Cost:** ~$0.05–0.10 per scan  
**LLM:** `anthropic/claude-sonnet-4-5` via OpenRouter  
**File:** `lib/agent-check/sonnet-scoring.ts`

### Input

Sonnet receives a single prompt containing:
- The target domain
- All Phase 1 results (status + evidence per check)
- All Phase 2 results (found, confidence, evidence, details per check) — or null if Phase 2 wasn't triggered for a check
- The scoring schema: each check's name, max points, and what each point tier means

### Output

```typescript
type ScoredCheck = {
  score: number
  maxScore: number
  found: boolean
  detectionMethod: "deterministic" | "ai_fallback"
  confidence: "high" | "medium" | "low" | null
  justification: string   // one sentence explaining the score
  evidence?: string
}

type SonnetScoringResult = {
  checks: Record<string, ScoredCheck>
}
```

### Scoring Nuance

Sonnet applies judgment rather than rigid rules. Examples:

- MCP server repo found but last commit 2 years ago → 5/10 with justification "Found archived MCP repo at github.com/…, inactive since 2023"
- OpenAPI spec exists but has 2 paths with no descriptions → 3/8 with justification "Spec found but minimal coverage (2 undocumented endpoints)"
- OAuth mentioned in docs as "coming soon" → 1/8 with justification "OAuth referenced in docs but marked as upcoming feature"
- High-confidence Phase 2 find → full points with `detectionMethod: "ai_fallback"`
- Low-confidence Phase 2 find → partial credit at Sonnet's discretion

The key principle: **Sonnet scores what was actually found, not what a rubric says to score.** The rubric (max points per check) is a ceiling, not a formula.

---

## Orchestrator Changes (`lib/agent-check/index.ts`)

```
1. Check Redis cache — return cached result if hit
2. Fetch homepage HTML (shared, cached in memory)
3. Run all Phase 1 checks in parallel (pass homepageHtml)
4. Identify checks with status NOT_FOUND or UNCERTAIN → needed set
5. [Phase 1.5] Run Sonnet Router:
   a. Extract nav/sitemap candidates from homepageHtml (deterministic)
   b. Call Sonnet to map best 3 URLs per check type + inject platform hints
   c. Fetch those pages in parallel → RouterOutput { pages, taskHints }
   d. Fallback to hardcoded paths if Sonnet call fails
6. Run Phase 2 Haiku sub-agents in parallel, passing (domain, pages, taskHint) per check
7. Call Sonnet synthesis with all Phase 1 + Phase 2 evidence
8. Assemble final BlockResult objects from SonnetScoringResult
9. Write result to Redis cache
```

---

## Caching

- **Store:** Upstash Redis
- **Key:** `agent-check:{normalizedHostname}` (e.g. `agent-check:github.com`)
- **TTL:** 24 hours
- **On hit:** Stream stored result immediately, skip all phases
- **On miss:** Run full scan, write result to cache after Sonnet synthesis

---

## Timing Budget

```
Homepage fetch:            ~1s
Phase 1 (parallel):        ≤8s
Phase 1.5 — discovery:     ~1s   (nav parsing + robots/sitemap fetch)
Phase 1.5 — Sonnet router: ~3s   (one Sonnet call)
Phase 1.5 — page fetches:  ~3s   (parallel, 3 URLs per check)
Phase 2 (parallel):        ≤15s  (only if triggered)
Sonnet synthesis:          ≤10s
Total:                     ≤42s  (worst case, all phases triggered)
```

Phase 1.5 adds ~6–7s on top of the original budget when fully triggered. If Phase 1 resolves all checks, Phase 1.5 is skipped entirely.

---

## Type Changes (`lib/agent-check/types.ts`)

Add to `CheckResult`:

```typescript
detectionMethod?: "deterministic" | "ai_fallback"
confidence?: "high" | "medium" | "low"
justification?: string
```

---

## What Does NOT Change

- Block structure and scoring weights (MCP=10, OpenAPI=8, etc.)
- Browser Operability block — still a stub, no Phase 2 needed
- API route (`app/api/agent-check/route.ts`) — unchanged
- UI components — unchanged (they consume richer `CheckResult` fields automatically via optional fields)

---

## New Files

| File | Purpose |
|---|---|
| `lib/agent-check/phase2-agents.ts` | 7 exported Haiku sub-agent functions |
| `lib/agent-check/sonnet-scoring.ts` | Sonnet synthesis function |
| `lib/agent-check/page-router.ts` | Phase 1.5: nav/sitemap discovery, Sonnet router call, page fetching, SSRF-safe URL filter |

## Modified Files

| File | Change |
|---|---|
| `lib/agent-check/index.ts` | Three-phase orchestration (Phase 1 → 1.5 → 2) + caching |
| `lib/agent-check/machine-interface.ts` | Return Phase1Result instead of BlockResult |
| `lib/agent-check/agent-discovery.ts` | Return Phase1Result instead of BlockResult |
| `lib/agent-check/auth-security.ts` | Return Phase1Result instead of BlockResult |
| `lib/agent-check/types.ts` | Add Phase1Status, Phase1Result, SubAgentResult, ScoredCheck, RouterOutput, RouterPageMap, RouterHintMap |
| `lib/agent-check/utils.ts` | Add Upstash Redis cache helpers |
| `lib/agent-check/phase2-agents.ts` | Agent signatures updated from `(url, homepageHtml)` to `(domain, pages, taskHint)` — agents no longer fetch their own pages |
