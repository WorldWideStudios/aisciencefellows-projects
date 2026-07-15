# Browser Operability Scan — Design Spec

**Date:** 2026-05-29
**Feature:** Real browser agent scan for the Agent Operability Report's Browser Operability block
**Status:** Approved

---

## 1. Problem

The Browser Operability block currently returns a hard-coded mock (score 0, status "pending"). The goal is to replace it with a real LLM agent that navigates the target site using a headless browser and reports what an AI agent can and cannot do there.

---

## 2. Approach

An LLM agent (Claude Haiku) drives a headless Chromium browser via Playwright using DOM-based tool calls. The agent explores the site freely for up to 15 turns, then emits a structured JSON assessment. No screenshots — DOM-only tools keep cost and latency low.

**Ruled out:**
- Screenshot / computer-use approach: 4-6x more tokens, 2x slower, not justified for this use case
- Static Playwright script + LLM scoring: loses the adaptive "agent perspective" that distinguishes this block

---

## 3. Architecture

No changes to the Next.js frontend API route or `callBrowserService()`. The `playwright-service` already exists as a separate Express app; it just becomes real.

```
POST /api/agent-check (Next.js)
  └─ callBrowserService(url)
       └─ POST playwright-service/scan { url }
            │
            ├─ Launch Playwright (headless Chromium)
            ├─ Open page at URL
            ├─ Start Claude Haiku session (15-turn cap, 45s timeout)
            │    Claude calls tools → Playwright executes → results back to Claude
            │
            ├─ Claude final message = structured JSON assessment
            └─ Return BrowserOperabilityResult
```

### New files in `playwright-service/src/`

| File | Purpose |
|---|---|
| `tools.ts` | 6 Playwright tool implementations + tool schema definitions |
| `agent.ts` | Claude session orchestrator: system prompt, turn loop, JSON extraction |
| `scanner.ts` | Wires Playwright page to agent, enforces 45s hard timeout |

`index.ts` (existing) routes `POST /scan` to `scanner.ts`.

---

## 4. Claude's Tool Set

All tools operate on the currently active Playwright page.

| Tool | Input | Output |
|---|---|---|
| `navigate` | `{ url: string }` | `{ title, statusCode, finalUrl }` |
| `get_page_content` | _(none)_ | `{ text, headings, links[] }` — visible text + top 50 links |
| `click_element` | `{ selectorOrText: string }` | `{ success, newUrl? }` |
| `fill_field` | `{ selector: string, value: string }` | `{ success }` |
| `get_forms` | _(none)_ | `{ forms: [{ action, fields: [{ name, type }] }] }` |
| `detect_blocking` | _(none)_ | `{ hasCaptcha, hasCfChallenge, statusCode, botSignals[] }` |

`get_page_content` caps output at 50 links and ~3000 chars of visible text to keep token usage bounded.

---

## 5. Session Design

```
Model:     claude-haiku-4-5-20251001
Max turns: 15
Timeout:   45s (hard kill — Playwright page closed, error result returned)
```

**System prompt (summary):**
> You are an AI agent testing whether this website can be operated by AI agents.
> Starting from the provided URL, use your tools to:
> 1. Load the homepage and detect any bot-blocking
> 2. Explore the main navigation (click 2-3 nav links)
> 3. Find forms and attempt to interact with them
> 4. Find the authentication flow (login/sign-up)
> 5. Note anything that would block or hinder an AI agent
>
> After your exploration, emit a JSON object (and nothing else) with this exact shape:
> `{ checks: { botBlocking, navigationWorking, formsInteractable, authFlowReachable, noJsWall }, blockers, sessionSummary }`

Claude is instructed to call `detect_blocking` first, then explore, then emit the final JSON as the last message.

---

## 6. Scoring Model

**Total: 25 points across 5 checks**

| Check | Max pts | Scoring logic |
|---|---|---|
| `botBlocking` | 6 | 6 = no blocking detected; 0 = blocked (CAPTCHA / CF challenge / 403) |
| `navigationWorking` | 6 | 6 = nav links resolve and SPA routing works; 0 = broken / unreachable |
| `formsInteractable` | 5 | 5 = forms found and fields typeable; 0 = no forms or all inaccessible |
| `authFlowReachable` | 4 | 4 = login or sign-up page reachable with form present; 0 = not found |
| `noJsWall` | 4 | 4 = core content visible in headless browser; 0 = blank/JS-wall |

Each check is **binary** (0 or full points). Claude assigns `found: bool`, `score: number`, and `evidence: string` per check.

For `botBlocking`, `found: true` means blocking **was detected** (score 0). For all other checks, `found: true` means the positive capability **was confirmed** (full score). The system prompt must make this distinction explicit.

**`blockers` array:** plain-language strings Claude emits for things that would impede an agent (e.g. `"hCaptcha on sign-up form"`, `"Login requires email verification before access"`). Displayed in the UI as a dedicated blockers list.

**`sessionSummary`:** one-sentence Claude-written summary shown in the report card.

---

## 7. Output Shape

```typescript
// Final JSON Claude emits:
{
  checks: {
    botBlocking:        { score: number, found: boolean, evidence: string },
    navigationWorking:  { score: number, found: boolean, evidence: string },
    formsInteractable:  { score: number, found: boolean, evidence: string },
    authFlowReachable:  { score: number, found: boolean, evidence: string },
    noJsWall:           { score: number, found: boolean, evidence: string },
  },
  blockers: string[],
  sessionSummary: string,
}
```

`scanner.ts` maps this to `BrowserOperabilityResult`, summing scores and setting `status: "complete"`. The `blockers` and `sessionSummary` fields are additions — `BrowserOperabilityResult` in `types.ts` must be extended to include them (`blockers?: string[]`, `sessionSummary?: string`).

---

## 8. Type Changes

`frontend/lib/agent-check/types.ts` — update `BrowserOperabilityChecks`:

```typescript
// Before:
export interface BrowserOperabilityChecks {
  semanticHtml: CheckResult
  ariaAttributes: CheckResult
  stableUrls: CheckResult
  keyboardNavigation: CheckResult
  noCaptcha: CheckResult
}

// After:
export interface BrowserOperabilityChecks {
  botBlocking: CheckResult
  navigationWorking: CheckResult
  formsInteractable: CheckResult
  authFlowReachable: CheckResult
  noJsWall: CheckResult
}
```

`frontend/lib/agent-check/browser-operability.ts` — remove the `status: "pending"` override so the real service status passes through.

---

## 9. Frontend Display

The existing `BrowserOperabilityResult` shape and SSE protocol are unchanged — the block streams in exactly like the other three blocks. The UI just renders different check names. The `blockers` array and `sessionSummary` are new fields — the frontend should display them if present (blockers as a callout list, summary as a subtitle on the block card).

---

## 10. Error Handling & Edge Cases

| Scenario | Behavior |
|---|---|
| 45s timeout | Hard kill Playwright page; return score 0 with `status: "complete"`, `sessionSummary: "Scan timed out"` |
| Claude fails to emit valid JSON | Parse best-effort; fall back to score 0 with error summary |
| Playwright fails to launch | Return score 0, log error |
| Site redirects to auth wall immediately | Claude detects via `detect_blocking` or `navigate` — scores `authFlowReachable: 4`, `navigationWorking: 0` |
| `PLAYWRIGHT_SERVICE_URL` not set | Existing MOCK fallback in `browser-operability.ts` stays unchanged |

---

## 11. Cost Estimate

- ~10 tool calls avg × ~300 tokens input + output = ~3000 tokens/scan
- Haiku: $0.80/M input, $4/M output → ~$0.003/scan
- Adds ~20-30s to scan time (in parallel with other blocks — net wall-clock impact is zero if other blocks finish first)

---

## 12. Deployment Note

Playwright requires a real Node.js server environment. The `playwright-service` already runs as a separate service (not on Vercel). No deployment architecture changes needed — just add `playwright` and `@anthropic-ai/sdk` as dependencies to `playwright-service/package.json`.
