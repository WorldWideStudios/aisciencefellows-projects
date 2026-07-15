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
import { runPageRouter } from "./page-router"
import type {
  AgentCheckResponse, BlockResult, SSEEvent,
  MachineInterfacePhase1Results, AgentDiscoveryPhase1Results, AuthSecurityPhase1Results,
  Phase2CheckName, SubAgentResult, ScoredCheck, RouterOutput,
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

function toCheckResult(sc: ScoredCheck | undefined, fallback: { score: number; maxScore: number }): import("./types").CheckResult {
  if (!sc) return fallback
  const { confidence, ...rest } = sc
  return { ...rest, confidence: confidence ?? undefined }
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
      mcpServer: toCheckResult(c.mcpServer, { score: 0, maxScore: 10 }),
      openApiSpec: toCheckResult(c.openApiSpec, { score: 0, maxScore: 8 }),
      apiDescriptionCoverage: toCheckResult(c.apiDescriptionCoverage, { score: 0, maxScore: 6 }),
      publicApiExists: toCheckResult(c.publicApiExists, { score: 0, maxScore: 6 }),
    },
  }

  const agentDiscovery: BlockResult = {
    score: (c.llmsTxt?.score ?? 0) + (c.robotsTxtAi?.score ?? 0) + (c.schemaOrg?.score ?? 0) + (c.sdkDocs?.score ?? 0),
    maxScore: 25,
    checks: {
      llmsTxt: toCheckResult(c.llmsTxt, { score: 0, maxScore: 8 }),
      robotsTxtAi: toCheckResult(c.robotsTxtAi, { score: 0, maxScore: 6 }),
      schemaOrg: toCheckResult(c.schemaOrg, { score: 0, maxScore: 6 }),
      sdkDocs: toCheckResult(c.sdkDocs, { score: 0, maxScore: 5 }),
    },
  }

  const authSecurity: BlockResult = {
    score: (c.oauth?.score ?? 0) + (c.apiKeySupport?.score ?? 0) + (c.corsPolicy?.score ?? 0),
    maxScore: 20,
    checks: {
      oauth: toCheckResult(c.oauth, { score: 0, maxScore: 8 }),
      apiKeySupport: toCheckResult(c.apiKeySupport, { score: 0, maxScore: 6 }),
      corsPolicy: toCheckResult(c.corsPolicy, { score: 0, maxScore: 6 }),
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

    const AI_BOTS = ["anthropic-ai", "gpt-bot", "claude-bot", "perplexity-bot", "cohere-ai", "google-extended", "amazonbot"]

    const machine: MachineInterfacePhase1Results = machineRes.status === "fulfilled"
      ? machineRes.value
      : { mcpServer: { status: "NOT_FOUND" }, openApiSpec: { status: "NOT_FOUND" }, publicApiExists: { status: "NOT_FOUND" } }

    const discovery: AgentDiscoveryPhase1Results = discoveryRes.status === "fulfilled"
      ? discoveryRes.value
      : { llmsTxt: { status: "NOT_FOUND" }, robotsTxtAi: { status: "FOUND", rawData: { allowedBots: [...AI_BOTS], blockedBots: [] } }, schemaOrg: { status: "NOT_FOUND" }, sdkDocs: { status: "NOT_FOUND" } }

    const auth: AuthSecurityPhase1Results = authRes.status === "fulfilled"
      ? authRes.value
      : { oauth: { status: "NOT_FOUND" }, apiKeySupport: { status: "NOT_FOUND" }, corsPolicy: { status: "NOT_FOUND" } }

    // Phase 2 — identify what needs agent resolution
    const phase2Needed = identifyPhase2Checks(machine, discovery, auth)

    // Phase 1.5 — Sonnet Router: discover real pages + inject platform hints
    const routerOutput = await runPageRouter(url, domain, homepageHtml, phase2Needed)

    // Phase 2 — Haiku sub-agents using router-provided pages and hints
    const phase2Results = await runPhase2(domain, phase2Needed, routerOutput)

    // Sonnet synthesis
    const scored = await scoreSonnet(domain, machine, discovery, auth, phase2Results)

    // Assemble final result
    const { machineInterface, agentDiscovery, authSecurity } = assembleBlocks(scored)
    const browserOperability = browserRes.status === "fulfilled"
      ? browserRes.value as AgentCheckResponse["blocks"]["browserOperability"]
      : { score: 0, maxScore: 25, status: "complete" as const, checks: {} }

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
