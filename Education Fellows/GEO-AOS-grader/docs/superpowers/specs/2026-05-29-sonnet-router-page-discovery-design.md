# Sonnet Router + Page Discovery Design

**Date:** 2026-05-29  
**Status:** Approved

## Problem

Phase 2 Haiku agents are failing to find things that clearly exist (e.g. GitHub scores 0/5 on SDK Docs and 0/6 on Schema.org). Root causes:

1. **Hardcoded page paths are wrong for most real sites.** Agents fetch `/developers`, `/product`, `/features` — paths that don't exist on GitHub, Stripe, or most large platforms.
2. **Content on subdomains is never reached.** GitHub's SDK docs are at `docs.github.com`, not `github.com/docs`. The current fetcher only looks at the same base domain.
3. **Phase 1 Schema.org only checks the homepage.** GitHub's homepage is a JS SPA — JSON-LD may not be present there even if it exists on other pages.
4. **Agents have no platform context.** A Haiku agent scanning GitHub has no idea it's GitHub or that Octokit is the SDK to look for.

## Solution: Phase 1.5 — Sonnet Router

Insert a routing step between Phase 1 and Phase 2 that:
1. Discovers real pages on the site (deterministic nav/sitemap crawl)
2. Uses Sonnet's world knowledge to supplement discovery and add platform-specific task hints
3. Feeds curated pages + hints into each Phase 2 Haiku agent

## Pipeline

```
Homepage fetch (single fetch, shared)
      ↓
Phase 1 — deterministic HTTP checks (unchanged)
      ↓
Phase 1.5 — Sonnet Router  ← NEW
  a) Nav/sitemap discovery (deterministic, no LLM)
  b) One Sonnet call → { pages, taskHints } per check type
      ↓
Phase 2 — Haiku agents (enhanced inputs)
  - Router-provided pages instead of hardcoded paths
  - Task hints injected into each agent prompt
      ↓
Phase 3 — Sonnet synthesis (unchanged)
```

Phase 1 is entirely untouched. The router only runs for checks that Phase 1 did not already resolve (same `identifyPhase2Checks` gate as today).

## Step A: Nav/Sitemap Discovery (deterministic)

From the already-fetched homepage HTML:

1. Extract `<a href>` from `<nav>`, `<header>`, `<footer>` elements (regex-based, no DOM parser dependency)
2. Also scan full HTML for links containing keywords: `docs`, `api`, `developer`, `sdk`, `library`, `reference`
3. Resolve relative URLs to absolute; filter to:
   - Same domain paths
   - Known doc subdomains: `docs.*`, `developer.*`, `api.*`, `dev.*`
4. Cap at 25 candidates

Then:
5. Fetch `robots.txt`, look for `Sitemap:` directive
6. If found, fetch sitemap, extract up to 20 URLs prioritising paths containing `doc`, `api`, `sdk`, `developer`
7. Deduplicate and cap final list at ~35 candidates

**Fallback:** if homepage HTML is empty or yields fewer than 3 links, append common fallback paths: `/docs`, `/developers`, `/api`, `/about`.

## Step B: Sonnet Router Call

**Input:**
- Domain name
- Homepage `<title>` and `<meta description>` (not full HTML — keeps token cost low)
- List of ~35 candidate URLs

**What Sonnet does:**
1. Identifies the platform if known ("GitHub — code hosting platform")
2. For each of 7 check types, returns the 3 best URLs to fetch — from the candidate list OR from world knowledge if candidates are missing something important
3. Returns a one-line task hint per check type

**Output schema:**
```json
{
  "platformHint": "GitHub — major code hosting and developer platform",
  "pages": {
    "mcpServer":       ["url", "url", "url"],
    "openApiSpec":     ["url", "url", "url"],
    "publicApiExists": ["url", "url", "url"],
    "schemaOrg":       ["url", "url", "url"],
    "sdkDocs":         ["url", "url", "url"],
    "oauth":           ["url", "url", "url"],
    "apiKeySupport":   ["url", "url", "url"]
  },
  "taskHints": {
    "mcpServer":       "GitHub has a community MCP server at github.com/github/github-mcp-server",
    "openApiSpec":     "",
    "publicApiExists": "",
    "schemaOrg":       "Check for SoftwareSourceCode or Organization @type values",
    "sdkDocs":         "GitHub's official SDK is Octokit (@octokit/core on npm)",
    "oauth":           "GitHub uses OAuth Apps and GitHub Apps — check docs.github.com/apps",
    "apiKeySupport":   "GitHub uses Personal Access Tokens (classic and fine-grained)"
  }
}
```

Empty string hints are allowed — Sonnet only fills in hints where it has genuine signal.

**Fallback:** if the Sonnet router call fails or returns malformed JSON, fall back to the current hardcoded paths per agent. Nothing in Phase 2 or Phase 3 changes.

**Cost:** ~$0.003–0.005 per scan (one Sonnet call with short input/output).

## Phase 2 Agent Changes

**Current:** each agent calls `fetchPages(baseUrl, hardcodedPaths)` internally.

**New:** `fetchPages` is removed from individual agent functions. Instead:
- The router fetches all needed pages upfront in parallel after the Sonnet call (one batch of HTTP fetches, each check type gets its 3 URLs fetched)
- Each agent function receives `(pages: string, taskHint: string)` instead of `(url: string, homepageHtml: string)`
- If `taskHint` is non-empty, it is appended to the agent's task prompt: `"\n\nPLATFORM HINT: ${taskHint}"`

Haiku agent logic is otherwise unchanged.

## Files Changed

| File | Change |
|------|--------|
| `frontend/lib/agent-check/page-router.ts` | **New** — nav extraction, sitemap fetch, Sonnet router call, page fetching |
| `frontend/lib/agent-check/phase2-agents.ts` | Agents accept `(pages: string, taskHint: string)` instead of fetching their own pages |
| `frontend/lib/agent-check/index.ts` | Insert Phase 1.5 between Phase 1 and Phase 2; pass router output into `runPhase2` |

No changes to: `agent-discovery.ts`, `machine-interface.ts`, `auth-security.ts`, `sonnet-scoring.ts`, any UI files, or the scoring rubric.

## Future: Browser Operability (Playwright)

This design deliberately leaves room for a browser-based agent layer. The current stack (raw HTTP fetches) has one fundamental limitation: JS-rendered pages return near-empty HTML. This affects:

- **Schema.org detection** — some sites inject JSON-LD via JavaScript, invisible to raw fetches
- **Nav link extraction** — SPA homepages render their nav client-side
- **Browser Operability block** — currently stubbed at 0 / "pending"

The planned evolution: a Playwright-based agent that actually navigates to the site, renders pages fully, attempts auth flows, clicks through onboarding, and tries API calls. This is the full "can an AI agent operate this site" test. The Playwright service infrastructure (`playwright-service/`) already exists in the repo.

When that lands, the router's nav extraction step should prefer Playwright-rendered HTML for the homepage over raw HTTP, since it produces accurate nav links and correct JSON-LD. Everything else in this design remains valid.
