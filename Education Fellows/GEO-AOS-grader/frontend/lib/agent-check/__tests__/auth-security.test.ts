import { describe, it, expect, vi, beforeEach } from "vitest"
import { checkAuthSecurityPhase1 } from "../auth-security"
import * as utils from "../utils"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)

function ok(body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), { status: 200, headers: { "Content-Type": "application/json", ...headers } })
}
function okText(body: string): Response { return new Response(body, { status: 200 }) }
function notFound(): Response { return new Response("Not Found", { status: 404 }) }

beforeEach(() => { mockFetch.mockReset() })

describe("oauth", () => {
  it("returns FOUND when /.well-known/oauth-authorization-server is valid JSON", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("oauth-authorization-server")) return Promise.resolve(ok({ issuer: "https://example.com" }))
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.oauth.status).toBe("FOUND")
    expect(r.oauth.evidence).toContain("well-known")
  })

  it("returns UNCERTAIN when OAuth 2.0 mentioned in /developers docs", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/developers")) return Promise.resolve(okText("<p>We support OAuth 2.0 flows.</p>"))
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.oauth.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no OAuth signal", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.oauth.status).toBe("NOT_FOUND")
  })
})

describe("apiKeySupport", () => {
  it("returns FOUND when /settings/api page mentions API key", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/settings/api")) return Promise.resolve(okText("Your API key: xxxx"))
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.apiKeySupport.status).toBe("FOUND")
  })

  it("returns UNCERTAIN when API key mentioned in /settings page", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/settings") && !url.includes("/api")) return Promise.resolve(okText("Manage your API key here."))
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.apiKeySupport.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no API key signal", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.apiKeySupport.status).toBe("NOT_FOUND")
  })
})

describe("corsPolicy", () => {
  it("returns FOUND with policy=* when CORS is wildcard", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/api")) return Promise.resolve(
        new Response(null, { status: 200, headers: { "Access-Control-Allow-Origin": "*" } })
      )
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.corsPolicy.status).toBe("FOUND")
    expect((r.corsPolicy.rawData as { policy: string }).policy).toBe("*")
  })

  it("returns UNCERTAIN when CORS is a specific origin", async () => {
    mockFetch.mockImplementation((url: string) => {
      if (url.includes("/api")) return Promise.resolve(
        new Response(null, { status: 200, headers: { "Access-Control-Allow-Origin": "https://app.example.com" } })
      )
      return Promise.resolve(notFound())
    })
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.corsPolicy.status).toBe("UNCERTAIN")
  })

  it("returns NOT_FOUND when no API endpoint and no CORS headers", async () => {
    mockFetch.mockResolvedValue(notFound())
    const r = await checkAuthSecurityPhase1("https://example.com", "")
    expect(r.corsPolicy.status).toBe("NOT_FOUND")
  })
})
