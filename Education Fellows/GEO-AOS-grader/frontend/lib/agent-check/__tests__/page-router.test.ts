import { describe, it, expect, vi, beforeEach } from "vitest"
import { extractNavLinks, buildCandidates, callSonnetRouter, runPageRouter, isSafeUrl } from "../page-router"
import * as utils from "../utils"
import type { Phase2CheckName } from "../types"

vi.mock("../utils", async importOriginal => {
  const actual = await importOriginal<typeof import("../utils")>()
  return { ...actual, fetchWithTimeout: vi.fn(), callOpenRouter: vi.fn() }
})

const mockFetch = vi.mocked(utils.fetchWithTimeout)
const mockOpenRouter = vi.mocked(utils.callOpenRouter)

function notFound(): Response { return new Response("Not Found", { status: 404 }) }
function okText(body: string): Response { return new Response(body, { status: 200 }) }

beforeEach(() => {
  mockFetch.mockReset()
  mockOpenRouter.mockReset()
})

describe("extractNavLinks", () => {
  it("extracts links from nav elements", () => {
    const html = `<nav><a href="/docs">Docs</a><a href="/api">API</a></nav>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).toContain("https://example.com/docs")
    expect(result).toContain("https://example.com/api")
  })

  it("includes doc subdomain links from nav", () => {
    const html = `<nav><a href="https://docs.example.com/sdk">SDK</a></nav>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).toContain("https://docs.example.com/sdk")
  })

  it("excludes external unrelated domains", () => {
    const html = `<nav><a href="https://twitter.com/example">Twitter</a></nav>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).not.toContain("https://twitter.com/example")
  })

  it("picks up keyword-bearing links outside structural elements", () => {
    const html = `<div><a href="/developers/sdk">SDK</a></div>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).toContain("https://example.com/developers/sdk")
  })

  it("ignores hash and query-only hrefs", () => {
    const html = `<nav><a href="#section">Section</a><a href="?tab=1">Tab</a></nav>`
    const result = extractNavLinks(html, "https://example.com")
    expect(result).toHaveLength(0)
  })
})

describe("buildCandidates", () => {
  it("merges nav links and sitemap candidates, capped at 35", async () => {
    const html = `<nav><a href="/docs">Docs</a></nav>`
    mockFetch
      .mockResolvedValueOnce(okText("Sitemap: https://example.com/sitemap.xml"))
      .mockResolvedValueOnce(okText(`
        <urlset>
          <url><loc>https://example.com/api/reference</loc></url>
          <url><loc>https://example.com/developers</loc></url>
        </urlset>
      `))
    const result = await buildCandidates(html, "https://example.com")
    expect(result).toContain("https://example.com/docs")
    expect(result).toContain("https://example.com/api/reference")
    expect(result.length).toBeLessThanOrEqual(35)
  })

  it("adds fallback paths when nav yields fewer than 3 links", async () => {
    const html = `<html></html>`
    mockFetch.mockResolvedValue(notFound())
    const result = await buildCandidates(html, "https://example.com")
    expect(result).toContain("https://example.com/docs")
  })

  it("deduplicates URLs across nav and sitemap", async () => {
    const html = `<nav><a href="/docs">Docs</a></nav>`
    mockFetch
      .mockResolvedValueOnce(okText("Sitemap: https://example.com/sitemap.xml"))
      .mockResolvedValueOnce(okText(`<urlset><url><loc>https://example.com/docs</loc></url></urlset>`))
    const result = await buildCandidates(html, "https://example.com")
    expect(result.filter(u => u === "https://example.com/docs")).toHaveLength(1)
  })
})

describe("callSonnetRouter", () => {
  it("returns parsed RouterOutput on valid Sonnet response", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      platformHint: "GitHub — code hosting",
      pages: {
        sdkDocs: ["https://docs.github.com/rest/overview/libraries"],
        schemaOrg: ["https://github.com/about"],
        mcpServer: [], openApiSpec: [], publicApiExists: [], oauth: [], apiKeySupport: [],
      },
      taskHints: {
        sdkDocs: "GitHub SDK is Octokit",
        schemaOrg: "",
        mcpServer: "", openApiSpec: "", publicApiExists: "", oauth: "", apiKeySupport: "",
      },
    }))
    const result = await callSonnetRouter("github.com", "GitHub", "Where the world builds software", ["https://github.com/about"])
    expect(result.platformHint).toBe("GitHub — code hosting")
    expect(result.pages.sdkDocs).toContain("https://docs.github.com/rest/overview/libraries")
    expect(result.taskHints.sdkDocs).toBe("GitHub SDK is Octokit")
  })

  it("throws on malformed JSON so runPageRouter can catch and fallback", async () => {
    mockOpenRouter.mockResolvedValue("not json {{{")
    await expect(callSonnetRouter("example.com", "", "", [])).rejects.toThrow()
  })
})

describe("runPageRouter", () => {
  it("fetches pages for needed checks using Sonnet-routed URLs", async () => {
    mockOpenRouter.mockResolvedValue(JSON.stringify({
      platformHint: "Example platform",
      pages: {
        sdkDocs: ["https://docs.example.com/sdk"],
        schemaOrg: ["https://example.com/about"],
        mcpServer: [], openApiSpec: [], publicApiExists: [], oauth: [], apiKeySupport: [],
      },
      taskHints: {
        sdkDocs: "Check for @example/sdk on npm",
        schemaOrg: "", mcpServer: "", openApiSpec: "", publicApiExists: "", oauth: "", apiKeySupport: "",
      },
    }))
    // Page fetches: robots.txt (404), sitemap.xml (404), then the routed pages
    mockFetch
      .mockResolvedValueOnce(notFound())
      .mockResolvedValueOnce(notFound())
      .mockResolvedValueOnce(okText("npm install @example/sdk"))
      .mockResolvedValueOnce(okText('<script type="application/ld+json">{"@type":"SoftwareApplication"}</script>'))

    const needed = new Set<Phase2CheckName>(["sdkDocs", "schemaOrg"])
    const result = await runPageRouter("https://example.com", "example.com", "<nav><a href='/docs'>Docs</a></nav>", needed)

    expect(result.pages.sdkDocs).toContain("npm install @example/sdk")
    expect(result.taskHints.sdkDocs).toBe("Check for @example/sdk on npm")
  })

  it("falls back to hardcoded paths when Sonnet call fails", async () => {
    mockOpenRouter.mockRejectedValue(new Error("network error"))
    mockFetch
      .mockResolvedValueOnce(notFound())
      .mockResolvedValueOnce(notFound())
      .mockResolvedValue(okText("fallback content"))

    const needed = new Set<Phase2CheckName>(["sdkDocs"])
    const result = await runPageRouter("https://example.com", "example.com", "", needed)

    expect(result.platformHint).toBe("")
    expect(result.pages.sdkDocs).toContain("fallback content")
  })

  it("returns empty output when needed set is empty", async () => {
    const result = await runPageRouter("https://example.com", "example.com", "", new Set())
    expect(result.platformHint).toBe("")
    expect(result.pages).toEqual({})
    expect(result.taskHints).toEqual({})
  })
})

describe("isSafeUrl", () => {
  it("allows https public URLs", () => {
    expect(isSafeUrl("https://docs.github.com/sdk")).toBe(true)
    expect(isSafeUrl("http://example.com/api")).toBe(true)
  })

  it("blocks private IP ranges", () => {
    expect(isSafeUrl("http://10.0.0.1/internal")).toBe(false)
    expect(isSafeUrl("http://192.168.1.1/admin")).toBe(false)
    expect(isSafeUrl("http://172.16.0.1/secret")).toBe(false)
  })

  it("blocks localhost", () => {
    expect(isSafeUrl("http://localhost/api")).toBe(false)
    expect(isSafeUrl("http://127.0.0.1/api")).toBe(false)
  })

  it("blocks non-http protocols", () => {
    expect(isSafeUrl("file:///etc/passwd")).toBe(false)
    expect(isSafeUrl("ftp://example.com")).toBe(false)
  })
})
