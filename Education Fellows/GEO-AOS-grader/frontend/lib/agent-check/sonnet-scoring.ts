import { callOpenRouter } from "./utils"
import { computeApiCoverage } from "./machine-interface"
import type {
  MachineInterfacePhase1Results,
  AgentDiscoveryPhase1Results,
  AuthSecurityPhase1Results,
  Phase2CheckName,
  SubAgentResult,
  SonnetScoringResult,
} from "./types"

const SONNET = "anthropic/claude-sonnet-4-5"

const ZERO_CHECKS: SonnetScoringResult = {
  checks: {
    mcpServer:              { score: 0, maxScore: 10, found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    openApiSpec:            { score: 0, maxScore: 8,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    apiDescriptionCoverage: { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    publicApiExists:        { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    llmsTxt:                { score: 0, maxScore: 8,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    robotsTxtAi:            { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    schemaOrg:              { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    sdkDocs:                { score: 0, maxScore: 5,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    oauth:                  { score: 0, maxScore: 8,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    apiKeySupport:          { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
    corsPolicy:             { score: 0, maxScore: 6,  found: false, detectionMethod: "deterministic", confidence: null, justification: "Scoring unavailable" },
  }
}

function buildEvidenceJson(
  domain: string,
  machine: MachineInterfacePhase1Results,
  discovery: AgentDiscoveryPhase1Results,
  auth: AuthSecurityPhase1Results,
  phase2: Partial<Record<Phase2CheckName, SubAgentResult>>
): string {
  const coverage = computeApiCoverage(
    machine.openApiSpec.rawData as Record<string, unknown> | undefined
  )
  return JSON.stringify({
    domain,
    phase1: {
      mcpServer: { status: machine.mcpServer.status, evidence: machine.mcpServer.evidence },
      openApiSpec: {
        status: machine.openApiSpec.status,
        evidence: machine.openApiSpec.evidence,
        coveragePercentage: coverage.percentage,
      },
      publicApiExists: { status: machine.publicApiExists.status, evidence: machine.publicApiExists.evidence },
      llmsTxt: { status: discovery.llmsTxt.status, rawData: discovery.llmsTxt.rawData },
      robotsTxtAi: { status: discovery.robotsTxtAi.status, rawData: discovery.robotsTxtAi.rawData },
      schemaOrg: { status: discovery.schemaOrg.status, rawData: discovery.schemaOrg.rawData },
      sdkDocs: { status: discovery.sdkDocs.status, evidence: discovery.sdkDocs.evidence },
      oauth: { status: auth.oauth.status, evidence: auth.oauth.evidence },
      apiKeySupport: { status: auth.apiKeySupport.status, evidence: auth.apiKeySupport.evidence },
      corsPolicy: { status: auth.corsPolicy.status, rawData: auth.corsPolicy.rawData },
    },
    phase2: Object.fromEntries(Object.entries(phase2)),
  }, null, 2)
}

function buildPrompt(evidenceJson: string): string {
  return `You are scoring an AI agent operability report. Based on the evidence below, assign a score to each check. Apply judgment — do not follow a rigid formula. The max score for each check is a ceiling.

SCORING RUBRIC:
- mcpServer (max 10): Active maintained server = 10; found but archived/old = 4–6; vague mention = 1–2
- openApiSpec (max 8): Complete spec with well-documented paths = 8; spec with some paths = 4–6; minimal/empty spec = 2
- apiDescriptionCoverage (max 6): >70% paths documented = 6; 40–70% = 4; 10–40% = 2; <10% = 0; no spec = 0
- publicApiExists (max 6): Dedicated developer portal = 6; API mentioned prominently = 3; vague = 1
- llmsTxt (max 8): Rich file with tool/action sections = 8; basic file with links = 3–5; minimal = 2; absent = 0
- robotsTxtAi (max 6): All AI bots allowed = 6; 1–2 blocked = 4; 3–4 blocked = 2; all blocked = 0
- schemaOrg (max 6): WebAPI or APIReference found = 6; SoftwareApplication or Action = 3–4; basic types = 1–2; none = 0
- sdkDocs (max 5): Multiple published packages = 5; one package = 3; SDK mentioned = 1; none = 0
- oauth (max 8): Well-known endpoint confirmed = 8; documented OAuth flow = 4; mentioned = 1; none = 0
- apiKeySupport (max 6): API key management page found = 6; keys documented = 3; mentioned = 1; none = 0
- corsPolicy (max 6): Wildcard * = 6; specific origin = 3; no CORS found = 1

EVIDENCE:
${evidenceJson}

Return ONLY valid JSON (no markdown, no other text) matching this exact schema. detectionMethod must be "deterministic" if found via phase1 status=FOUND, or "ai_fallback" if found only via phase2:
{
  "checks": {
    "mcpServer": { "score": 0, "maxScore": 10, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "openApiSpec": { "score": 0, "maxScore": 8, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "apiDescriptionCoverage": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "publicApiExists": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "llmsTxt": { "score": 0, "maxScore": 8, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "robotsTxtAi": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "schemaOrg": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "sdkDocs": { "score": 0, "maxScore": 5, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "oauth": { "score": 0, "maxScore": 8, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "apiKeySupport": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" },
    "corsPolicy": { "score": 0, "maxScore": 6, "found": false, "detectionMethod": "deterministic", "confidence": null, "justification": "one sentence", "evidence": "" }
  }
}`
}

export async function scoreSonnet(
  domain: string,
  machine: MachineInterfacePhase1Results,
  discovery: AgentDiscoveryPhase1Results,
  auth: AuthSecurityPhase1Results,
  phase2: Partial<Record<Phase2CheckName, SubAgentResult>>
): Promise<SonnetScoringResult> {
  try {
    const evidenceJson = buildEvidenceJson(domain, machine, discovery, auth, phase2)
    const prompt = buildPrompt(evidenceJson)
    const raw = await callOpenRouter(SONNET, prompt, 2000)
    const content = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim()
    const parsed = JSON.parse(content) as SonnetScoringResult
    if (!parsed?.checks || typeof parsed.checks !== "object") return ZERO_CHECKS
    return parsed
  } catch { return ZERO_CHECKS }
}
