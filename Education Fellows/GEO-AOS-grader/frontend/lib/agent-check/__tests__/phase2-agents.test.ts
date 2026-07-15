import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkMcpServerAgent, checkOpenApiSpecAgent, checkOAuthAgent } from "../phase2-agents"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, callOpenRouter: vi.fn() }
})

const mockOpenRouter = vi.mocked(utils.callOpenRouter)

beforeEach(() => { mockOpenRouter.mockReset() })

const PAGES = "--- /docs ---\n<html>some page content</html>"

describe("checkMcpServerAgent", () => {
  it("returns found=true when Haiku identifies an MCP repo", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: true,
      confidence: "high",
      evidence: "https://github.com/example/mcp-server",
      details: "Official MCP server repository",
    }))
    const result = await checkMcpServerAgent("example.com", PAGES, "")
    expect(result.found).toBe(true)
    expect(result.confidence).toBe("high")
    expect(result.evidence).toContain("github.com")
  })

  it("returns found=false when Haiku finds nothing", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: false,
      confidence: "high",
      evidence: "",
    }))
    const result = await checkMcpServerAgent("example.com", PAGES, "")
    expect(result.found).toBe(false)
  })

  it("returns safe fallback on OpenRouter error", async () => {
    mockOpenRouter.mockRejectedValue(new Error("timeout"))
    const result = await checkMcpServerAgent("example.com", PAGES, "")
    expect(result.found).toBe(false)
    expect(result.confidence).toBe("low")
  })

  it("injects task hint into the prompt sent to Haiku", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({ found: false, confidence: "low", evidence: "" }))
    await checkMcpServerAgent("example.com", PAGES, "Check github.com/example/mcp for the server")
    const calledPrompt = mockOpenRouter.mock.calls[0][1] as string
    expect(calledPrompt).toContain("PLATFORM HINT: Check github.com/example/mcp for the server")
  })
})

describe("checkOpenApiSpecAgent", () => {
  it("returns found=true when Haiku finds a spec URL in pre-fetched pages", async () => {
    const pages = "--- /api ---\n<a href='/api/spec.json'>OpenAPI</a>"
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      found: true,
      confidence: "high",
      evidence: "https://example.com/api/spec.json",
    }))
    const result = await checkOpenApiSpecAgent("example.com", pages, "")
    expect(result.found).toBe(true)
    expect(result.evidence).toContain("spec.json")
  })
})

describe("checkOAuthAgent", () => {
  it("returns found=false with safe fallback on JSON parse error", async () => {
    mockOpenRouter.mockResolvedValue("not valid json at all {{{")
    const result = await checkOAuthAgent("example.com", PAGES, "")
    expect(result.found).toBe(false)
    expect(result.confidence).toBe("low")
  })
})
