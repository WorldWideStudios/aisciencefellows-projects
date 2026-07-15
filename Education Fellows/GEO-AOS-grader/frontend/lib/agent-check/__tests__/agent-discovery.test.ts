import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkAgentDiscoveryPhase1 } from "../agent-discovery"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: string, ct = "text/plain"): Response {
  return new Response(body, { status: 200, headers: { "Content-Type": ct } })
}
function notFound(): Response { return new Response("Not Found", { status: 404 }) }

beforeEach(() => { mockFetch.mockReset() })

describe("llmsTxt", () => {
  it("returns NOT_FOUND when /llms.txt is 404", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.llmsTxt.status).toBe("NOT_FOUND")
  })

  it("returns FOUND with wordCount when /llms.txt is 200", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/llms.txt")) return Promise.resolve(ok("# Hello world\nThis is content."))
      return Promise.resolve(notFound())
    })
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.llmsTxt.status).toBe("FOUND")
    expect((r.llmsTxt.rawData as { wordCount: number }).wordCount).toBeGreaterThan(0)
  })

  it("records hasActionSections=true when llms.txt has ## Tools section", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/llms.txt")) return Promise.resolve(ok("# Intro\n## Tools\nsome tool"))
      return Promise.resolve(notFound())
    })
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect((r.llmsTxt.rawData as { hasActionSections: boolean }).hasActionSections).toBe(true)
  })
})

describe("robotsTxtAi", () => {
  it("returns FOUND with empty blockedBots when robots.txt is 404", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.robotsTxtAi.status).toBe("FOUND")
    expect((r.robotsTxtAi.rawData as { blockedBots: string[] }).blockedBots).toHaveLength(0)
  })

  it("returns FOUND with all AI bots in blockedBots when wildcard Disallow: /", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/robots.txt")) return Promise.resolve(ok("User-agent: *\nDisallow: /"))
      return Promise.resolve(notFound())
    })
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    const rawData = r.robotsTxtAi.rawData as { blockedBots: string[] }
    expect(rawData.blockedBots.length).toBeGreaterThan(0)
  })
})

describe("schemaOrg", () => {
  it("returns NOT_FOUND when no JSON-LD in homepageHtml", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAgentDiscoveryPhase1("https://example.com", "<p>No schema here</p>")
    expect(r.schemaOrg.status).toBe("NOT_FOUND")
  })

  it("returns FOUND when JSON-LD with SoftwareApplication in homepageHtml", async () => {
    mockFetch.mockResolvedValue(notFound())
    const html = `<script type="application/ld+json">{"@type":"SoftwareApplication","name":"Test"}</script>`
    const r = await checkAgentDiscoveryPhase1("https://example.com", html)
    expect(r.schemaOrg.status).toBe("FOUND")
    expect((r.schemaOrg.rawData as { typesFound: string[] }).typesFound).toContain("SoftwareApplication")
  })
})

describe("sdkDocs", () => {
  it("returns NOT_FOUND when no SDK signals", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.sdkDocs.status).toBe("NOT_FOUND")
  })

  it("returns FOUND when signals >= 5", async () => {
    mockFetch.mockImplementation((url: string) => {
      // npmjs.com (2) + npm install (2) + pip install (2) = 6 signals
      if (url.includes("/developers")) return Promise.resolve(ok('<a href="https://npmjs.com/package/example">npm</a><p>npm install example</p><p>pip install example</p>'))
      return Promise.resolve(notFound())
    })
    const r = await checkAgentDiscoveryPhase1("https://example.com", "")
    expect(r.sdkDocs.status).toBe("FOUND")
  })
})
