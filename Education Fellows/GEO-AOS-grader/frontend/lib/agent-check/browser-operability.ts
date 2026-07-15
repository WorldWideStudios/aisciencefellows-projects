import type { BrowserOperabilityResult } from "./types"

const MOCK: BrowserOperabilityResult = {
  score: 0,
  maxScore: 25,
  status: "complete",
  checks: {
    botBlocking:       { score: 0, maxScore: 6,  evidence: "Browser scan not available" },
    navigationWorking: { score: 0, maxScore: 6,  evidence: "Browser scan not available" },
    formsInteractable: { score: 0, maxScore: 5,  evidence: "Browser scan not available" },
    authFlowReachable: { score: 0, maxScore: 4,  evidence: "Browser scan not available" },
    noJsWall:          { score: 0, maxScore: 4,  evidence: "Browser scan not available" },
  },
  blockers: [],
  sessionSummary: "Browser scan requires the Playwright service to be configured.",
}

export async function callBrowserService(url: string): Promise<BrowserOperabilityResult> {
  const serviceUrl = process.env.PLAYWRIGHT_SERVICE_URL
  if (!serviceUrl) return MOCK

  try {
    const res = await fetch(`${serviceUrl}/scan`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
      signal: AbortSignal.timeout(150000),
    })
    if (!res.ok) return MOCK
    return await res.json() as BrowserOperabilityResult
  } catch {
    return MOCK
  }
}
