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
