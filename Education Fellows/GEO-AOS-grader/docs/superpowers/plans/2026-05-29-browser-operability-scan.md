# Browser Operability Scan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the mocked Browser Operability block with a real Claude Haiku agent that drives a headless Chromium browser to assess AI agent operability.

**Architecture:** The existing `playwright-service` Express app gains Playwright + Anthropic SDK. Claude Haiku explores the target site using 6 DOM-based tools for up to 15 turns, then emits a structured JSON assessment. The Next.js frontend's `callBrowserService()` already handles calling this service; only the timeout and status-override need updating there.

**Tech Stack:** Playwright (headless Chromium), @anthropic-ai/sdk (Claude Haiku tool-use), Express (existing), Jest + ts-jest (new tests), TypeScript

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `playwright-service/package.json` | Modify | Add playwright, @anthropic-ai/sdk, jest, ts-jest, @types/jest |
| `playwright-service/jest.config.js` | Create | Jest config for ts-jest |
| `playwright-service/.env.example` | Modify | Add ANTHROPIC_API_KEY |
| `playwright-service/src/types.ts` | Rewrite | New AgentAssessment, AgentCheckResult, updated BrowserOperabilityResult |
| `playwright-service/src/tools.ts` | Create | 6 Playwright tool schemas + executeTool dispatcher |
| `playwright-service/src/__tests__/tools.test.ts` | Create | Tool schema shape tests + executeTool routing |
| `playwright-service/src/agent.ts` | Create | SYSTEM_PROMPT, parseAssessment, runBrowserAgent |
| `playwright-service/src/__tests__/agent.test.ts` | Create | parseAssessment unit tests |
| `playwright-service/src/scanner.ts` | Create | isSafeUrl, scanUrl (launches browser, calls agent, 45s timeout) |
| `playwright-service/src/index.ts` | Rewrite | Wire /scan to scanUrl instead of mock |
| `frontend/lib/agent-check/types.ts` | Modify | Update BrowserOperabilityChecks, extend BrowserOperabilityResult |
| `frontend/lib/agent-check/browser-operability.ts` | Modify | Update MOCK names, remove status override, increase timeout to 60s |

---

## Task 1: Add Dependencies and Jest Config

**Files:**
- Modify: `playwright-service/package.json`
- Create: `playwright-service/jest.config.js`
- Modify: `playwright-service/.env.example`

- [ ] **Step 1: Update package.json**

Replace the entire contents of `playwright-service/package.json` with:

```json
{
  "name": "playwright-service",
  "version": "0.1.0",
  "private": true,
  "main": "dist/index.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/index.js",
    "dev": "ts-node src/index.ts",
    "test": "jest"
  },
  "dependencies": {
    "@anthropic-ai/sdk": "^0.51.0",
    "express": "^4.18.2",
    "playwright": "^1.52.0"
  },
  "devDependencies": {
    "@types/express": "^4.17.21",
    "@types/jest": "^29.5.14",
    "@types/node": "^22",
    "jest": "^29.7.0",
    "ts-jest": "^29.3.4",
    "ts-node": "^10.9.2",
    "typescript": "^5"
  }
}
```

- [ ] **Step 2: Create jest.config.js**

Create `playwright-service/jest.config.js`:

```js
module.exports = {
  preset: "ts-jest",
  testEnvironment: "node",
  testMatch: ["**/__tests__/**/*.test.ts"],
}
```

- [ ] **Step 3: Update .env.example**

Replace the entire contents of `playwright-service/.env.example` with:

```
PORT=3001
ANTHROPIC_API_KEY=your-key-here
```

- [ ] **Step 4: Install dependencies**

```bash
cd playwright-service && npm install
```

- [ ] **Step 5: Install Playwright's Chromium browser**

```bash
cd playwright-service && npx playwright install chromium
```

Expected output: Chromium download progress, ends with "✓ chromium ... is already installed" or similar.

- [ ] **Step 6: Verify Jest works**

```bash
cd playwright-service && npm test
```

Expected: "Test Suites: 0 passed, 0 total" (no test files yet — that's fine).

- [ ] **Step 7: Commit**

```bash
git add playwright-service/package.json playwright-service/jest.config.js playwright-service/.env.example playwright-service/package-lock.json
git commit -m "feat(playwright-service): add playwright, anthropic sdk, jest deps"
```

---

## Task 2: Update playwright-service Types

**Files:**
- Rewrite: `playwright-service/src/types.ts`

- [ ] **Step 1: Rewrite types.ts**

Replace the entire contents of `playwright-service/src/types.ts` with:

```typescript
export interface AgentCheckResult {
  score: number
  maxScore: number
  found: boolean
  evidence: string
}

export interface AgentAssessment {
  checks: {
    botBlocking: AgentCheckResult
    navigationWorking: AgentCheckResult
    formsInteractable: AgentCheckResult
    authFlowReachable: AgentCheckResult
    noJsWall: AgentCheckResult
  }
  blockers: string[]
  sessionSummary: string
}

export interface BrowserOperabilityResult {
  status: "complete"
  score: number
  maxScore: number
  checks: {
    botBlocking: AgentCheckResult
    navigationWorking: AgentCheckResult
    formsInteractable: AgentCheckResult
    authFlowReachable: AgentCheckResult
    noJsWall: AgentCheckResult
  }
  blockers: string[]
  sessionSummary: string
}

export interface ScanRequest {
  url: string
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd playwright-service && npx tsc --noEmit
```

Expected: no errors (index.ts will have errors about the old types — that's fine; we fix it in Task 6).

- [ ] **Step 3: Commit**

```bash
git add playwright-service/src/types.ts
git commit -m "feat(playwright-service): replace old check types with agent-centric checks"
```

---

## Task 3: Implement tools.ts with Tests

**Files:**
- Create: `playwright-service/src/tools.ts`
- Create: `playwright-service/src/__tests__/tools.test.ts`

- [ ] **Step 1: Write the failing tests first**

Create `playwright-service/src/__tests__/tools.test.ts`:

```typescript
import { BROWSER_TOOLS, executeTool } from "../tools"
import type { Page } from "playwright"

function makeMockPage(overrides: Partial<Record<string, unknown>> = {}): Page {
  return {
    goto: jest.fn().mockResolvedValue({ status: () => 200 }),
    title: jest.fn().mockResolvedValue("Test Page"),
    url: jest.fn().mockReturnValue("https://example.com"),
    evaluate: jest.fn().mockResolvedValue(""),
    locator: jest.fn().mockReturnValue({
      or: jest.fn().mockReturnThis(),
      first: jest.fn().mockReturnThis(),
      click: jest.fn().mockResolvedValue(undefined),
    }),
    getByText: jest.fn().mockReturnValue({
      or: jest.fn().mockReturnThis(),
      first: jest.fn().mockReturnThis(),
      click: jest.fn().mockResolvedValue(undefined),
    }),
    fill: jest.fn().mockResolvedValue(undefined),
    ...overrides,
  } as unknown as Page
}

describe("BROWSER_TOOLS schemas", () => {
  it("defines exactly 6 tools", () => {
    expect(BROWSER_TOOLS).toHaveLength(6)
  })

  it("each tool has name, description, and input_schema with type=object", () => {
    for (const tool of BROWSER_TOOLS) {
      expect(typeof tool.name).toBe("string")
      expect(typeof tool.description).toBe("string")
      expect(tool.input_schema).toBeDefined()
      expect(tool.input_schema.type).toBe("object")
    }
  })

  it("defines the expected tool names in order", () => {
    const names = BROWSER_TOOLS.map(t => t.name)
    expect(names).toEqual([
      "navigate",
      "get_page_content",
      "click_element",
      "fill_field",
      "get_forms",
      "detect_blocking",
    ])
  })

  it("navigate tool requires a url property", () => {
    const navigate = BROWSER_TOOLS.find(t => t.name === "navigate")!
    expect(navigate.input_schema.properties).toHaveProperty("url")
    expect(navigate.input_schema.required).toContain("url")
  })

  it("click_element tool requires selectorOrText", () => {
    const click = BROWSER_TOOLS.find(t => t.name === "click_element")!
    expect(click.input_schema.properties).toHaveProperty("selectorOrText")
    expect(click.input_schema.required).toContain("selectorOrText")
  })
})

describe("executeTool", () => {
  it("navigate calls page.goto with the provided url and returns status + finalUrl", async () => {
    const page = makeMockPage()
    const result = await executeTool("navigate", { url: "https://example.com" }, page) as Record<string, unknown>
    expect(page.goto).toHaveBeenCalledWith("https://example.com", expect.objectContaining({ waitUntil: "domcontentloaded" }))
    expect(result.statusCode).toBe(200)
    expect(result.finalUrl).toBe("https://example.com")
  })

  it("navigate handles null response (navigation failure) gracefully", async () => {
    const page = makeMockPage({ goto: jest.fn().mockResolvedValue(null) })
    const result = await executeTool("navigate", { url: "https://example.com" }, page) as Record<string, unknown>
    expect(result.statusCode).toBeNull()
  })

  it("returns error object for unknown tool name", async () => {
    const page = makeMockPage()
    const result = await executeTool("unknown_tool", {}, page) as Record<string, unknown>
    expect(result.error).toMatch(/Unknown tool/)
  })

  it("fill_field calls page.fill with selector and value", async () => {
    const page = makeMockPage()
    const result = await executeTool("fill_field", { selector: "input[name=email]", value: "test@example.com" }, page) as Record<string, unknown>
    expect(page.fill).toHaveBeenCalledWith("input[name=email]", "test@example.com", expect.any(Object))
    expect(result.success).toBe(true)
  })

  it("fill_field returns success=false if page.fill throws", async () => {
    const page = makeMockPage({ fill: jest.fn().mockRejectedValue(new Error("not found")) })
    const result = await executeTool("fill_field", { selector: "#nope", value: "x" }, page) as Record<string, unknown>
    expect(result.success).toBe(false)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd playwright-service && npm test
```

Expected: FAIL — "Cannot find module '../tools'"

- [ ] **Step 3: Implement tools.ts**

Create `playwright-service/src/tools.ts`:

```typescript
import type { Tool } from "@anthropic-ai/sdk/resources/messages"
import type { Page } from "playwright"

export const BROWSER_TOOLS: Tool[] = [
  {
    name: "navigate",
    description: "Navigate to a URL. Returns page title, HTTP status code, and final URL after redirects.",
    input_schema: {
      type: "object" as const,
      properties: {
        url: { type: "string", description: "The URL to navigate to" },
      },
      required: ["url"],
    },
  },
  {
    name: "get_page_content",
    description: "Get the current page's visible text (up to 3000 chars), h1-h3 headings, and top 50 links.",
    input_schema: {
      type: "object" as const,
      properties: {},
      required: [],
    },
  },
  {
    name: "click_element",
    description: "Click an element by CSS selector or visible text. Returns success and new URL if navigation occurred.",
    input_schema: {
      type: "object" as const,
      properties: {
        selectorOrText: { type: "string", description: "CSS selector or visible text of the element to click" },
      },
      required: ["selectorOrText"],
    },
  },
  {
    name: "fill_field",
    description: "Type a value into an input field identified by CSS selector.",
    input_schema: {
      type: "object" as const,
      properties: {
        selector: { type: "string", description: "CSS selector for the input field" },
        value: { type: "string", description: "Value to type into the field" },
      },
      required: ["selector", "value"],
    },
  },
  {
    name: "get_forms",
    description: "Get all forms on the current page with their action URLs and field names/types.",
    input_schema: {
      type: "object" as const,
      properties: {},
      required: [],
    },
  },
  {
    name: "detect_blocking",
    description: "Check the current page for bot-blocking: CAPTCHA widgets, Cloudflare challenges, suspicious status codes.",
    input_schema: {
      type: "object" as const,
      properties: {},
      required: [],
    },
  },
]

export async function executeTool(
  name: string,
  input: Record<string, unknown>,
  page: Page
): Promise<unknown> {
  switch (name) {
    case "navigate": {
      const response = await page.goto(input.url as string, { waitUntil: "domcontentloaded", timeout: 10000 }).catch(() => null)
      return {
        title: await page.title().catch(() => ""),
        statusCode: response?.status() ?? null,
        finalUrl: page.url(),
      }
    }

    case "get_page_content": {
      const text = await page.evaluate(() => document.body?.innerText ?? "").catch(() => "")
      const headings = await page.evaluate(() =>
        Array.from(document.querySelectorAll("h1, h2, h3")).slice(0, 10).map(el => el.textContent?.trim() ?? "")
      ).catch(() => [] as string[])
      const links = await page.evaluate(() =>
        Array.from(document.querySelectorAll("a[href]")).slice(0, 50).map(el => ({
          text: (el as HTMLAnchorElement).textContent?.trim().slice(0, 60) ?? "",
          href: (el as HTMLAnchorElement).href,
        }))
      ).catch(() => [] as { text: string; href: string }[])
      return { text: text.slice(0, 3000), headings, links }
    }

    case "click_element": {
      const selectorOrText = input.selectorOrText as string
      try {
        await page.locator(selectorOrText).or(page.getByText(selectorOrText)).first().click({ timeout: 5000 })
        return { success: true, newUrl: page.url() }
      } catch {
        return { success: false, newUrl: page.url() }
      }
    }

    case "fill_field": {
      try {
        await page.fill(input.selector as string, input.value as string, { timeout: 5000 })
        return { success: true }
      } catch {
        return { success: false }
      }
    }

    case "get_forms": {
      const forms = await page.evaluate(() =>
        Array.from(document.querySelectorAll("form")).map(form => ({
          action: (form as HTMLFormElement).action ?? "",
          fields: Array.from(form.querySelectorAll("input, textarea, select")).map(el => ({
            name: (el as HTMLInputElement).name || (el as HTMLInputElement).id || "",
            type: (el as HTMLInputElement).type || el.tagName.toLowerCase(),
          })),
        }))
      ).catch(() => [] as { action: string; fields: { name: string; type: string }[] }[])
      return { forms }
    }

    case "detect_blocking": {
      const hasCaptcha = await page.evaluate(() => {
        const iframeSrc = document.querySelector("iframe")?.src ?? ""
        return iframeSrc.includes("hcaptcha") || iframeSrc.includes("recaptcha") ||
          !!document.querySelector(".h-captcha, .g-recaptcha, [data-sitekey]")
      }).catch(() => false)

      const hasCfChallenge = await page.evaluate(() =>
        document.title.includes("Just a moment") ||
        !!document.querySelector("#cf-challenge-running, #cf-error-details")
      ).catch(() => false)

      const botSignals = await page.evaluate(() => {
        const signals: string[] = []
        if (document.title.includes("Access denied")) signals.push("access-denied-title")
        if (document.title.includes("403")) signals.push("403-in-title")
        if (document.title.includes("Attention Required")) signals.push("attention-required-title")
        return signals
      }).catch(() => [] as string[])

      return { hasCaptcha, hasCfChallenge, botSignals }
    }

    default:
      return { error: `Unknown tool: ${name}` }
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd playwright-service && npm test
```

Expected: all tests in `tools.test.ts` pass.

- [ ] **Step 5: Commit**

```bash
git add playwright-service/src/tools.ts playwright-service/src/__tests__/tools.test.ts
git commit -m "feat(playwright-service): implement browser tools with tests"
```

---

## Task 4: Implement agent.ts with Tests

**Files:**
- Create: `playwright-service/src/agent.ts`
- Create: `playwright-service/src/__tests__/agent.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `playwright-service/src/__tests__/agent.test.ts`:

```typescript
import { parseAssessment } from "../agent"

const VALID_ASSESSMENT = {
  checks: {
    botBlocking:       { score: 6, maxScore: 6, found: false, evidence: "No blocking detected during 5-page exploration" },
    navigationWorking: { score: 6, maxScore: 6, found: true,  evidence: "Nav links resolved, SPA routing functional" },
    formsInteractable: { score: 5, maxScore: 5, found: true,  evidence: "Contact form with 3 fields, all typeable" },
    authFlowReachable: { score: 4, maxScore: 4, found: true,  evidence: "Login page at /login with email+password form" },
    noJsWall:          { score: 4, maxScore: 4, found: true,  evidence: "Homepage rendered content in headless mode" },
  },
  blockers: [],
  sessionSummary: "Site is fully navigable by an AI agent",
}

describe("parseAssessment", () => {
  it("parses valid assessment JSON", () => {
    const result = parseAssessment(JSON.stringify(VALID_ASSESSMENT))
    expect(result.checks.botBlocking.score).toBe(6)
    expect(result.checks.navigationWorking.found).toBe(true)
    expect(result.checks.formsInteractable.evidence).toBe("Contact form with 3 fields, all typeable")
    expect(result.blockers).toEqual([])
    expect(result.sessionSummary).toBe("Site is fully navigable by an AI agent")
  })

  it("strips markdown code fences before parsing", () => {
    const wrapped = "```json\n" + JSON.stringify(VALID_ASSESSMENT) + "\n```"
    const result = parseAssessment(wrapped)
    expect(result.checks.botBlocking.score).toBe(6)
  })

  it("strips plain code fences before parsing", () => {
    const wrapped = "```\n" + JSON.stringify(VALID_ASSESSMENT) + "\n```"
    const result = parseAssessment(wrapped)
    expect(result.checks.navigationWorking.found).toBe(true)
  })

  it("returns fallback for invalid JSON", () => {
    const result = parseAssessment("not valid json at all")
    expect(result.sessionSummary).toBe("Scan failed or timed out")
    expect(result.blockers).toEqual(["Scan could not be completed"])
    expect(result.checks.botBlocking.score).toBe(0)
  })

  it("returns fallback for empty string", () => {
    const result = parseAssessment("")
    expect(result.sessionSummary).toBe("Scan failed or timed out")
  })

  it("returns fallback when checks object is missing", () => {
    const result = parseAssessment(JSON.stringify({ blockers: [], sessionSummary: "x" }))
    expect(result.sessionSummary).toBe("Scan failed or timed out")
  })

  it("returns fallback when a required check key is missing", () => {
    const partial = {
      checks: { botBlocking: { score: 6, maxScore: 6, found: false, evidence: "x" } },
      blockers: [],
      sessionSummary: "partial",
    }
    const result = parseAssessment(JSON.stringify(partial))
    expect(result.sessionSummary).toBe("Scan failed or timed out")
  })

  it("returns fallback when score is not a number", () => {
    const bad = {
      ...VALID_ASSESSMENT,
      checks: {
        ...VALID_ASSESSMENT.checks,
        botBlocking: { score: "six", maxScore: 6, found: false, evidence: "x" },
      },
    }
    const result = parseAssessment(JSON.stringify(bad))
    expect(result.sessionSummary).toBe("Scan failed or timed out")
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd playwright-service && npm test -- --testPathPattern=agent
```

Expected: FAIL — "Cannot find module '../agent'"

- [ ] **Step 3: Implement agent.ts**

Create `playwright-service/src/agent.ts`:

```typescript
import Anthropic from "@anthropic-ai/sdk"
import type { MessageParam, ToolResultBlockParam } from "@anthropic-ai/sdk/resources/messages"
import type { Page } from "playwright"
import { BROWSER_TOOLS, executeTool } from "./tools"
import type { AgentAssessment } from "./types"

export const FALLBACK_ASSESSMENT: AgentAssessment = {
  checks: {
    botBlocking:       { score: 0, maxScore: 6, found: false, evidence: "Scan failed" },
    navigationWorking: { score: 0, maxScore: 6, found: false, evidence: "Scan failed" },
    formsInteractable: { score: 0, maxScore: 5, found: false, evidence: "Scan failed" },
    authFlowReachable: { score: 0, maxScore: 4, found: false, evidence: "Scan failed" },
    noJsWall:          { score: 0, maxScore: 4, found: false, evidence: "Scan failed" },
  },
  blockers: ["Scan could not be completed"],
  sessionSummary: "Scan failed or timed out",
}

export const SYSTEM_PROMPT = `You are an AI agent testing whether a website can be operated by AI agents. Your job is to explore the site using the provided tools and assess how easy it is for an AI agent to navigate and interact with it.

Start by calling detect_blocking to check for bot-blocking, then navigate to the URL and explore. Try to:
1. Load the homepage and check if content is visible (noJsWall)
2. Navigate 2-3 internal links from the main navigation (navigationWorking)
3. Find and inspect any forms on the site (formsInteractable)
4. Find a login or sign-up page (authFlowReachable)

After your exploration, emit a JSON object as your final message (no other text, no markdown):
{
  "checks": {
    "botBlocking":       { "score": 0 or 6,  "maxScore": 6, "found": boolean, "evidence": "one sentence" },
    "navigationWorking": { "score": 0 or 6,  "maxScore": 6, "found": boolean, "evidence": "one sentence" },
    "formsInteractable": { "score": 0 or 5,  "maxScore": 5, "found": boolean, "evidence": "one sentence" },
    "authFlowReachable": { "score": 0 or 4,  "maxScore": 4, "found": boolean, "evidence": "one sentence" },
    "noJsWall":          { "score": 0 or 4,  "maxScore": 4, "found": boolean, "evidence": "one sentence" }
  },
  "blockers": ["plain-language description of each blocker, or empty array if none"],
  "sessionSummary": "one sentence summary of overall agent operability"
}

IMPORTANT scoring rules:
- botBlocking: found=true means blocking WAS detected (score=0). found=false means no blocking (score=6).
- All other checks: found=true means the capability works correctly (full score). found=false means it failed or was not found (score=0).`

export function parseAssessment(text: string): AgentAssessment {
  try {
    const clean = text.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim()
    if (!clean) return FALLBACK_ASSESSMENT
    const parsed = JSON.parse(clean) as AgentAssessment
    if (!parsed?.checks || typeof parsed.checks !== "object") return FALLBACK_ASSESSMENT
    const required = ["botBlocking", "navigationWorking", "formsInteractable", "authFlowReachable", "noJsWall"] as const
    for (const key of required) {
      if (!parsed.checks[key] || typeof parsed.checks[key].score !== "number") return FALLBACK_ASSESSMENT
    }
    return parsed
  } catch {
    return FALLBACK_ASSESSMENT
  }
}

export async function runBrowserAgent(
  url: string,
  page: Page,
  client: Anthropic,
  maxTurns = 15
): Promise<AgentAssessment> {
  const messages: MessageParam[] = [
    { role: "user", content: `Scan this URL for AI agent operability: ${url}` },
  ]

  for (let turn = 0; turn < maxTurns; turn++) {
    const response = await client.messages.create({
      model: "claude-haiku-4-5-20251001",
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      tools: BROWSER_TOOLS,
      messages,
    })

    if (response.stop_reason === "end_turn") {
      const textBlock = response.content.find(b => b.type === "text")
      return parseAssessment(textBlock?.type === "text" ? textBlock.text : "")
    }

    const toolResults: ToolResultBlockParam[] = []
    for (const block of response.content) {
      if (block.type === "tool_use") {
        const result = await executeTool(block.name, block.input as Record<string, unknown>, page)
        toolResults.push({
          type: "tool_result",
          tool_use_id: block.id,
          content: JSON.stringify(result),
        })
      }
    }

    messages.push({ role: "assistant", content: response.content })
    messages.push({ role: "user", content: toolResults })
  }

  // Max turns reached — prompt for final JSON
  messages.push({ role: "user", content: "You have reached the maximum number of steps. Emit your final JSON assessment now, with no other text." })
  const final = await client.messages.create({
    model: "claude-haiku-4-5-20251001",
    max_tokens: 1024,
    system: SYSTEM_PROMPT,
    messages,
  })
  const textBlock = final.content.find(b => b.type === "text")
  return parseAssessment(textBlock?.type === "text" ? textBlock.text : "")
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd playwright-service && npm test -- --testPathPattern=agent
```

Expected: all 8 tests in `agent.test.ts` pass.

- [ ] **Step 5: Run all tests to make sure nothing broke**

```bash
cd playwright-service && npm test
```

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add playwright-service/src/agent.ts playwright-service/src/__tests__/agent.test.ts
git commit -m "feat(playwright-service): implement claude agent with parseAssessment"
```

---

## Task 5: Implement scanner.ts

**Files:**
- Create: `playwright-service/src/scanner.ts`

- [ ] **Step 1: Create scanner.ts**

Create `playwright-service/src/scanner.ts`:

```typescript
import { chromium } from "playwright"
import Anthropic from "@anthropic-ai/sdk"
import { runBrowserAgent } from "./agent"
import type { BrowserOperabilityResult, AgentAssessment } from "./types"

const SCAN_TIMEOUT_MS = 45_000

const MAX_SCORES: Record<keyof AgentAssessment["checks"], number> = {
  botBlocking: 6,
  navigationWorking: 6,
  formsInteractable: 5,
  authFlowReachable: 4,
  noJsWall: 4,
}

function isSafeUrl(url: string): boolean {
  try {
    const u = new URL(url)
    if (u.protocol !== "https:" && u.protocol !== "http:") return false
    const h = u.hostname.toLowerCase()
    if (h === "localhost" || h === "127.0.0.1" || h === "::1") return false
    const ipv4 = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/)
    if (ipv4) {
      const [, a, b] = ipv4.map(Number)
      if (a === 10) return false
      if (a === 172 && b >= 16 && b <= 31) return false
      if (a === 192 && b === 168) return false
    }
    return true
  } catch { return false }
}

function buildFailedResult(sessionSummary: string, blockers: string[]): BrowserOperabilityResult {
  return {
    status: "complete",
    score: 0,
    maxScore: 25,
    checks: {
      botBlocking:       { score: 0, maxScore: 6, found: false, evidence: "Scan failed" },
      navigationWorking: { score: 0, maxScore: 6, found: false, evidence: "Scan failed" },
      formsInteractable: { score: 0, maxScore: 5, found: false, evidence: "Scan failed" },
      authFlowReachable: { score: 0, maxScore: 4, found: false, evidence: "Scan failed" },
      noJsWall:          { score: 0, maxScore: 4, found: false, evidence: "Scan failed" },
    },
    blockers,
    sessionSummary,
  }
}

function assessmentToResult(assessment: AgentAssessment): BrowserOperabilityResult {
  const checks = Object.fromEntries(
    (Object.keys(MAX_SCORES) as (keyof typeof MAX_SCORES)[]).map(key => [
      key,
      { ...assessment.checks[key], maxScore: MAX_SCORES[key] },
    ])
  ) as BrowserOperabilityResult["checks"]
  const score = Object.values(checks).reduce((sum, c) => sum + c.score, 0)
  return {
    status: "complete",
    score,
    maxScore: 25,
    checks,
    blockers: assessment.blockers,
    sessionSummary: assessment.sessionSummary,
  }
}

export async function scanUrl(url: string): Promise<BrowserOperabilityResult> {
  if (!isSafeUrl(url)) {
    return buildFailedResult(
      "URL rejected: not a safe public URL",
      ["URL is not a publicly accessible address"]
    )
  }

  const apiKey = process.env.ANTHROPIC_API_KEY
  if (!apiKey) {
    return buildFailedResult("Service misconfigured: ANTHROPIC_API_KEY not set", ["Internal configuration error"])
  }

  const client = new Anthropic({ apiKey })
  const browser = await chromium.launch({ headless: true }).catch(() => null)
  if (!browser) {
    return buildFailedResult("Failed to launch browser", ["Internal browser error"])
  }

  const page = await browser.newPage()

  try {
    const assessment = await Promise.race([
      runBrowserAgent(url, page, client),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error("timeout")), SCAN_TIMEOUT_MS)
      ),
    ])
    return assessmentToResult(assessment)
  } catch {
    return buildFailedResult("Scan timed out or encountered an error", ["Scan could not be completed within the time limit"])
  } finally {
    await browser.close().catch(() => undefined)
  }
}
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
cd playwright-service && npx tsc --noEmit
```

Expected: no errors from scanner.ts, agent.ts, or tools.ts. index.ts may still error about the old mock types — that is fixed in Task 6.

- [ ] **Step 3: Commit**

```bash
git add playwright-service/src/scanner.ts
git commit -m "feat(playwright-service): implement scanUrl with playwright + 45s timeout"
```

---

## Task 6: Update index.ts

**Files:**
- Rewrite: `playwright-service/src/index.ts`

- [ ] **Step 1: Rewrite index.ts**

Replace the entire contents of `playwright-service/src/index.ts` with:

```typescript
import express from "express"
import { scanUrl } from "./scanner"
import type { ScanRequest } from "./types"

const app = express()
app.use(express.json())

app.post("/scan", async (req, res) => {
  const { url } = req.body as ScanRequest
  if (!url || typeof url !== "string") {
    res.status(400).json({ error: "url is required" })
    return
  }
  console.log(`[scan] requested for: ${url}`)
  try {
    const result = await scanUrl(url)
    res.json(result)
  } catch (err) {
    console.error("[scan] error:", err)
    res.status(500).json({ error: "scan failed" })
  }
})

app.get("/health", (_req, res) => {
  res.json({ status: "ok" })
})

const port = process.env.PORT ?? 3001
app.listen(port, () => {
  console.log(`Playwright service listening on port ${port}`)
})
```

- [ ] **Step 2: Verify everything compiles**

```bash
cd playwright-service && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run all tests**

```bash
cd playwright-service && npm test
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add playwright-service/src/index.ts
git commit -m "feat(playwright-service): wire /scan to real scanUrl"
```

---

## Task 7: Update Frontend Types

**Files:**
- Modify: `frontend/lib/agent-check/types.ts`

- [ ] **Step 1: Update BrowserOperabilityChecks and BrowserOperabilityResult**

In `frontend/lib/agent-check/types.ts`, replace the two interfaces:

```typescript
// BEFORE — replace this:
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
```

With:

```typescript
export interface BrowserOperabilityChecks {
  botBlocking: CheckResult
  navigationWorking: CheckResult
  formsInteractable: CheckResult
  authFlowReachable: CheckResult
  noJsWall: CheckResult
}

export interface BrowserOperabilityResult extends BlockResult {
  status: "pending" | "complete"
  checks: Record<keyof BrowserOperabilityChecks, CheckResult>
  blockers?: string[]
  sessionSummary?: string
}
```

- [ ] **Step 2: Verify frontend TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors (browser-operability.ts will have type errors about the old check names — those are fixed in Task 8).

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm test -- --passWithNoTests
```

Expected: existing tests pass (or no tests affected).

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/agent-check/types.ts
git commit -m "feat: update BrowserOperabilityChecks to agent-centric check names"
```

---

## Task 8: Update browser-operability.ts

**Files:**
- Modify: `frontend/lib/agent-check/browser-operability.ts`

- [ ] **Step 1: Rewrite browser-operability.ts**

Replace the entire contents of `frontend/lib/agent-check/browser-operability.ts` with:

```typescript
import type { BrowserOperabilityResult } from "./types"

const MOCK: BrowserOperabilityResult = {
  score: 0,
  maxScore: 25,
  status: "pending",
  checks: {
    botBlocking:       { score: 0, maxScore: 6 },
    navigationWorking: { score: 0, maxScore: 6 },
    formsInteractable: { score: 0, maxScore: 5 },
    authFlowReachable: { score: 0, maxScore: 4 },
    noJsWall:          { score: 0, maxScore: 4 },
  },
}

export async function callBrowserService(url: string): Promise<BrowserOperabilityResult> {
  const serviceUrl = process.env.PLAYWRIGHT_SERVICE_URL
  if (!serviceUrl) return MOCK

  try {
    const res = await fetch(`${serviceUrl}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      signal: AbortSignal.timeout(60000),
    })
    if (!res.ok) return MOCK
    return await res.json() as BrowserOperabilityResult
  } catch {
    return MOCK
  }
}
```

Key changes from the old file:
- MOCK uses new check names with correct maxScores
- Removed `// Always "pending" until V1.0 — override service status` and the `{ ...MOCK, ...data, status: "pending" }` spread
- Timeout increased from 10 000 ms to 60 000 ms to accommodate the 45s scan

- [ ] **Step 2: Verify frontend TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: all existing tests pass.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/agent-check/browser-operability.ts
git commit -m "feat: wire browser-operability to real service, remove pending override"
```

---

## Task 9: Add ANTHROPIC_API_KEY to playwright-service .env

This step is manual and environment-specific.

- [ ] **Step 1: Create .env in playwright-service (if not present)**

Copy `playwright-service/.env.example` to `playwright-service/.env` and fill in the key:

```
PORT=3001
ANTHROPIC_API_KEY=sk-ant-...your-real-key...
```

The `.env` file should already be in `.gitignore`. Verify:

```bash
cat .gitignore | grep .env
```

Expected output includes `.env`.

---

## Task 10: Smoke Test End-to-End

- [ ] **Step 1: Start playwright-service in dev mode**

```bash
cd playwright-service && npm run dev
```

Expected: `Playwright service listening on port 3001`

- [ ] **Step 2: Send a test scan request**

In a new terminal:

```bash
curl -s -X POST http://localhost:3001/scan \
  -H "Content-Type: application/json" \
  -d '{"url":"https://stripe.com"}' | python3 -m json.tool
```

Expected: JSON with `status: "complete"`, 5 checks with scores, a `sessionSummary`, and a `blockers` array. Scan takes 20-40s.

- [ ] **Step 3: Start the full frontend**

```bash
cd frontend && npm run dev
```

- [ ] **Step 4: Run a full agent report**

Navigate to `http://localhost:3000/agent-report`, submit a URL. Verify the Browser Operability block:
- Shows real scores (not all zeros)
- Shows `status: "complete"` (not "pending")
- Displays the new check names: Bot Blocking, Navigation Working, Forms Interactable, Auth Flow Reachable, No JS Wall

- [ ] **Step 5: Final commit**

```bash
git add -p  # review any stray changes
git commit -m "feat: browser operability scan v1 — real claude haiku agent with playwright"
```
