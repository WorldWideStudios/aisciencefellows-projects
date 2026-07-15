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

  it("parses JSON when prose precedes a fenced block", () => {
    const wrapped = "Excellent! All checks complete. Here's my assessment:\n\n```json\n" + JSON.stringify(VALID_ASSESSMENT) + "\n```"
    const result = parseAssessment(wrapped)
    expect(result.checks.botBlocking.score).toBe(6)
    expect(result.sessionSummary).toBe("Site is fully navigable by an AI agent")
  })

  it("parses JSON when prose surrounds a bare object", () => {
    const wrapped = "Here is the result: " + JSON.stringify(VALID_ASSESSMENT) + " Let me know if you need anything else."
    const result = parseAssessment(wrapped)
    expect(result.checks.noJsWall.score).toBe(4)
  })

  it("parses JSON containing braces inside string values", () => {
    const withBraces = {
      ...VALID_ASSESSMENT,
      sessionSummary: "Found a template literal ${foo} and a JSON snippet {\"a\":1} in page text",
    }
    const result = parseAssessment("```json\n" + JSON.stringify(withBraces) + "\n```")
    expect(result.checks.botBlocking.score).toBe(6)
    expect(result.sessionSummary).toContain("template literal")
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
