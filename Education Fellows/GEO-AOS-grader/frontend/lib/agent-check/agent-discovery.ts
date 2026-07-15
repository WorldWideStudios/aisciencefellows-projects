import { fetchWithTimeout } from "./utils"
import type { Phase1Result, AgentDiscoveryPhase1Results } from "./types"

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }

const AI_BOTS = ["anthropic-ai", "gpt-bot", "claude-bot", "perplexity-bot", "cohere-ai", "google-extended", "amazonbot"]
const ACTION_SECTIONS = ["## api", "## tools", "## actions", "## capabilities", "## integrations"]

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

// Backward compatibility wrapper for index.ts (temporary)
export async function checkAgentDiscovery(baseUrl: string) {
  const phase1 = await checkAgentDiscoveryPhase1(baseUrl, "")
  return {
    score: 0,
    maxScore: 25,
    checks: {
      llmsTxt: { score: 0, maxScore: 8, found: phase1.llmsTxt.status === "FOUND" },
      robotsTxtAi: { score: 0, maxScore: 6, found: phase1.robotsTxtAi.status === "FOUND" },
      schemaOrg: { score: 0, maxScore: 6, found: phase1.schemaOrg.status === "FOUND" },
      sdkDocs: { score: 0, maxScore: 5, found: phase1.sdkDocs.status === "FOUND" },
    },
  }
}
