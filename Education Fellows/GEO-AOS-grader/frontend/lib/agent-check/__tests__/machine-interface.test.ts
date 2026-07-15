import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkMachineInterfacePhase1, computeApiCoverage } from "../machine-interface"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: unknown): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json" } })
}
function notFound(): Response { return new Response("Not Found", { status: 404 }) }
function okText(body: string): Response {
  return new Response(body, { status: 200, headers: { "Content-Type": "text/plain" } })
}

beforeEach(() => { mockFetch.mockReset() })

describe("mcpServer", () => {
  it("returns FOUND immediately for known platforms (github.com)", async () => {
    const result = await checkMachineInterfacePhase1("https://github.com", "")
    expect(result.mcpServer.status).toBe("FOUND")
    expect(result.mcpServer.evidence).toContain("github-mcp-server")
  })

  it("returns FOUND when /.well-known/mcp.json returns 200", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/.well-known/mcp.json")) return Promise.resolve(ok({}))
      return Promise.resolve(notFound())
    })
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.mcpServer.status).toBe("FOUND")
  })

  it("returns UNCERTAIN when homepage HTML mentions MCP", async () => {
    mockFetch.mockResolvedValue(notFound())
    const html = "<p>We support model context protocol for agent integration.</p>"
    const result = await checkMachineInterfacePhase1("https://example.com", html)
    expect(result.mcpServer.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no signals present", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.mcpServer.status).toBe("NOT_FOUND")
  })
})

describe("openApiSpec", () => {
  it("returns FOUND with rawData when spec has paths", async () => {
    const spec = { openapi: "3.0.0", paths: { "/users": { get: { summary: "List" } } } }
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/openapi.json")) return Promise.resolve(ok(spec))
      return Promise.resolve(notFound())
    })
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.openApiSpec.status).toBe("FOUND")
    expect(result.openApiSpec.rawData).toBeDefined()
    expect(result.openApiSpec.evidence).toContain("openapi.json")
  })

  it("returns UNCERTAIN when spec exists but has no paths", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/openapi.json")) return Promise.resolve(ok({ openapi: "3.0.0" }))
      return Promise.resolve(notFound())
    })
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.openApiSpec.status).toBe("UNCERTAIN")
  })

  it("returns FOUND for known platform spec URL (github.com)", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("rest-api-description"))
        return Promise.resolve(ok({ openapi: "3.0.0", paths: { "/repos": {} } }))
      return Promise.resolve(notFound())
    })
    const result = await checkMachineInterfacePhase1("https://github.com", "")
    expect(result.openApiSpec.status).toBe("FOUND")
  })

  it("returns NOT_FOUND when all paths return 404", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkMachineInterfacePhase1("https://example.com", "")
    expect(result.openApiSpec.status).toBe("NOT_FOUND")
  })
})

describe("publicApiExists", () => {
  it("returns FOUND when 2+ signals in homepage HTML", async () => {
    mockFetch.mockResolvedValue(notFound())
    const html = '<a href="/api/v1">API</a><p>Check out our Developers section</p>'
    const result = await checkMachineInterfacePhase1("https://example.com", html)
    expect(result.publicApiExists.status).toBe("FOUND")
  })

  it("returns UNCERTAIN when 1 signal in homepage HTML", async () => {
    mockFetch.mockResolvedValue(notFound())
    const html = '<a href="/developers">Developers</a>'
    const result = await checkMachineInterfacePhase1("https://example.com", html)
    expect(result.publicApiExists.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no API signals", async () => {
    mockFetch.mockResolvedValue(notFound())
    const result = await checkMachineInterfacePhase1("https://example.com", "<p>Hello world</p>")
    expect(result.publicApiExists.status).toBe("NOT_FOUND")
  })
})

describe("computeApiCoverage", () => {
  it("returns 100% for fully documented spec", () => {
    const spec = {
      paths: { "/a": { get: { summary: "Get A" } }, "/b": { post: { description: "Post B" } } }
    }
    expect(computeApiCoverage(spec).percentage).toBe(100)
  })

  it("returns null for undefined spec", () => {
    expect(computeApiCoverage(undefined).percentage).toBeNull()
  })
})
