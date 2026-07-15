import { chromium } from "playwright"
import OpenAI from "openai"
import { runBrowserAgent } from "./agent"
import type { BrowserOperabilityResult, AgentAssessment } from "./types"

const SCAN_TIMEOUT_MS = 120_000

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
      if (a === 0) return false
      if (a === 10) return false
      if (a === 127) return false
      if (a === 169 && b === 254) return false
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

  const apiKey = process.env.OPENROUTER_API_KEY
  if (!apiKey) {
    return buildFailedResult("Service misconfigured: OPENROUTER_API_KEY not set", ["Internal configuration error"])
  }

  const client = new OpenAI({
    apiKey,
    baseURL: "https://openrouter.ai/api/v1",
  })

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
  } catch (err) {
    console.error("[scanner] scan error:", err)
    return buildFailedResult("Scan timed out or encountered an error", ["Scan could not be completed within the time limit"])
  } finally {
    await browser.close().catch(() => undefined)
  }
}
