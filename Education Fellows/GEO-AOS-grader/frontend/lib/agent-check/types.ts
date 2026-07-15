export interface CheckResult {
  score: number
  maxScore: number
  found?: boolean
  url?: string
  evidence?: string
  detectionMethod?: "deterministic" | "ai_fallback"
  confidence?: "high" | "medium" | "low"
  justification?: string
}

export interface BlockResult {
  score: number
  maxScore: number
  checks: Record<string, CheckResult>
}

export interface AgentCheckResponse {
  domain: string
  scannedAt: string
  totalScore: number
  grade: string
  gradeColor: string
  blocks: {
    machineInterface: BlockResult
    browserOperability: BlockResult & { status: "pending" | "complete" }
    agentDiscovery: BlockResult
    authSecurity: BlockResult
  }
}

export type SSEEvent =
  | { type: "block"; block: keyof AgentCheckResponse["blocks"]; result: BlockResult }
  | { type: "complete"; result: AgentCheckResponse }
  | { type: "error"; message: string }

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

// ── Phase 1 ──────────────────────────────────────────────────────────────────

export type Phase1Status = "FOUND" | "NOT_FOUND" | "UNCERTAIN"

export interface Phase1Result {
  status: Phase1Status
  evidence?: string   // URL, quoted text, or description of what was found
  rawData?: unknown   // parsed spec object, HTML excerpt, structured metadata
}

export interface MachineInterfacePhase1Results {
  mcpServer: Phase1Result
  openApiSpec: Phase1Result
  publicApiExists: Phase1Result
}

export interface AgentDiscoveryPhase1Results {
  llmsTxt: Phase1Result
  robotsTxtAi: Phase1Result
  schemaOrg: Phase1Result
  sdkDocs: Phase1Result
}

export interface AuthSecurityPhase1Results {
  oauth: Phase1Result
  apiKeySupport: Phase1Result
  corsPolicy: Phase1Result
}

// ── Phase 2 ──────────────────────────────────────────────────────────────────

export interface SubAgentResult {
  found: boolean
  confidence: "high" | "medium" | "low"
  evidence: string    // URL or quoted text snippet
  details?: string    // extra context (repo age, package name, etc.)
}

export type Phase2CheckName =
  | "mcpServer"
  | "openApiSpec"
  | "publicApiExists"
  | "schemaOrg"
  | "sdkDocs"
  | "oauth"
  | "apiKeySupport"

// ── Page Router ───────────────────────────────────────────────────────────────

export type RouterPageMap = Partial<Record<Phase2CheckName, string>>
export type RouterHintMap = Partial<Record<Phase2CheckName, string>>

export interface RouterOutput {
  platformHint: string
  pages: RouterPageMap      // pre-fetched HTML content per check type
  taskHints: RouterHintMap  // one-line platform-specific hint per check type
}

// ── Sonnet Scoring ────────────────────────────────────────────────────────────

export interface ScoredCheck {
  score: number
  maxScore: number
  found: boolean
  detectionMethod: "deterministic" | "ai_fallback"
  confidence: "high" | "medium" | "low" | null
  justification: string
  evidence?: string
}

export interface SonnetScoringResult {
  checks: Record<string, ScoredCheck>
}
