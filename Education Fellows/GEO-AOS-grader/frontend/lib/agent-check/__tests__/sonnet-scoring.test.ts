import { describe, it, expect, vi, beforeEach } from "vitest"
import { scoreSonnet } from "../sonnet-scoring"
import * as utils from "../utils"
import type {
  MachineInterfacePhase1Results,
  AgentDiscoveryPhase1Results,
  AuthSecurityPhase1Results,
} from "../types"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, callOpenRouter: vi.fn() }
})

const mockOpenRouter = vi.mocked(utils.callOpenRouter)

beforeEach(() => { mockOpenRouter.mockReset() })

const machine: MachineInterfacePhase1Results = {
  mcpServer: { status: "FOUND", evidence: "https://github.com/example/mcp" },
  openApiSpec: { status: "FOUND", evidence: "https://example.com/openapi.json", rawData: { paths: { "/a": { get: { summary: "A" } } } } },
  publicApiExists: { status: "FOUND", evidence: "2 signals" },
}
const discovery: AgentDiscoveryPhase1Results = {
  llmsTxt: { status: "NOT_FOUND" },
  robotsTxtAi: { status: "FOUND", rawData: { allowedBots: ["anthropic-ai"], blockedBots: [] } },
  schemaOrg: { status: "NOT_FOUND" },
  sdkDocs: { status: "UNCERTAIN", evidence: "1 weak signal" },
}
const auth: AuthSecurityPhase1Results = {
  oauth: { status: "FOUND", evidence: "https://example.com/.well-known/oauth-authorization-server" },
  apiKeySupport: { status: "NOT_FOUND" },
  corsPolicy: { status: "FOUND", rawData: { policy: "*" } },
}

const validSonnetOutput = JSON.stringify({
  checks: {
    mcpServer: { score: 10, maxScore: 10, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Official MCP server found", evidence: "https://github.com/example/mcp" },
    openApiSpec: { score: 7, maxScore: 8, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Spec found with 1 path", evidence: "https://example.com/openapi.json" },
    apiDescriptionCoverage: { score: 6, maxScore: 6, found: true, detectionMethod: "deterministic", confidence: "high", justification: "100% documented", evidence: "" },
    publicApiExists: { score: 6, maxScore: 6, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Clear API signals", evidence: "2 signals" },
    llmsTxt: { score: 0, maxScore: 8, found: false, detectionMethod: "deterministic", confidence: null, justification: "No llms.txt found", evidence: "" },
    robotsTxtAi: { score: 6, maxScore: 6, found: true, detectionMethod: "deterministic", confidence: "high", justification: "All AI bots allowed", evidence: "" },
    schemaOrg: { score: 0, maxScore: 6, found: false, detectionMethod: "deterministic", confidence: null, justification: "No JSON-LD found", evidence: "" },
    sdkDocs: { score: 1, maxScore: 5, found: true, detectionMethod: "ai_fallback", confidence: "medium", justification: "Weak SDK signal", evidence: "1 weak signal" },
    oauth: { score: 8, maxScore: 8, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Well-known OAuth endpoint confirmed", evidence: "https://example.com/.well-known/oauth-authorization-server" },
    apiKeySupport: { score: 0, maxScore: 6, found: false, detectionMethod: "deterministic", confidence: null, justification: "No API key support found", evidence: "" },
    corsPolicy: { score: 6, maxScore: 6, found: true, detectionMethod: "deterministic", confidence: "high", justification: "Wildcard CORS policy", evidence: "" },
  }
})

describe("scoreSonnet", () => {
  it("maps Sonnet JSON output to SonnetScoringResult", async () => {
    mockOpenRouter.mockResolvedValue(validSonnetOutput)
    const result = await scoreSonnet("example.com", machine, discovery, auth, {})
    expect(result.checks.mcpServer.score).toBe(10)
    expect(result.checks.mcpServer.justification).toBe("Official MCP server found")
    expect(result.checks.oauth.detectionMethod).toBe("deterministic")
  })

  it("calls OpenRouter with claude-sonnet-4-5 model", async () => {
    mockOpenRouter.mockResolvedValue(validSonnetOutput)
    await scoreSonnet("example.com", machine, discovery, auth, {})
    expect(mockOpenRouter).toHaveBeenCalledWith(
      "anthropic/claude-sonnet-4-5",
      expect.stringContaining("example.com"),
      expect.any(Number)
    )
  })

  it("returns zero-score fallback on OpenRouter error", async () => {
    mockOpenRouter.mockRejectedValue(new Error("timeout"))
    const result = await scoreSonnet("example.com", machine, discovery, auth, {})
    expect(result.checks).toBeDefined()
    expect(Object.values(result.checks).every(c => c.score === 0)).toBe(true)
  })

  it("returns zero-score fallback on malformed JSON", async () => {
    mockOpenRouter.mockResolvedValue("not json {{{{")
    const result = await scoreSonnet("example.com", machine, discovery, auth, {})
    expect(Object.values(result.checks).every(c => c.score === 0)).toBe(true)
  })
})
