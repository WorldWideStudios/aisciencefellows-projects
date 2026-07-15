import { fetchWithTimeout } from "./utils"
import type { Phase1Result, MachineInterfacePhase1Results } from "./types"

const OPENAPI_PATHS = [
  "/openapi.json", "/openapi.yaml", "/swagger.json", "/swagger.yaml",
  "/api-docs", "/api-docs/swagger.json", "/api/openapi.json", "/api/openapi.yaml",
  "/api/v1/openapi.json", "/api/v2/openapi.json", "/api/v3/openapi.json",
  "/v1/openapi.json", "/v2/openapi.json", "/docs/api.json", "/docs/openapi.json",
  "/api/swagger.json", "/spec/openapi.json", "/.well-known/openapi.json",
]

const KNOWN_OPENAPI_SPECS: Record<string, string> = {
  "github.com": "https://raw.githubusercontent.com/github/rest-api-description/main/descriptions/api.github.com/api.github.com.json",
  "stripe.com": "https://raw.githubusercontent.com/stripe/openapi/master/openapi/spec3.json",
  "twilio.com": "https://raw.githubusercontent.com/twilio/twilio-oai/main/spec/json/twilio_api_v2010.json",
  "shopify.com": "https://shopify.dev/docs/api/admin-rest.json",
  "atlassian.com": "https://developer.atlassian.com/cloud/jira/platform/swagger-v3.v3.json",
}

const KNOWN_MCP_SERVERS: Record<string, string> = {
  "github.com": "https://github.com/github/github-mcp-server",
  "notion.com": "https://github.com/makenotion/notion-mcp-server",
  "notion.so": "https://github.com/makenotion/notion-mcp-server",
  "linear.app": "https://github.com/linear/linear-mcp",
  "stripe.com": "https://github.com/stripe/agent-toolkit",
  "atlassian.com": "https://github.com/sooperset/mcp-atlassian",
  "figma.com": "https://github.com/figma/figma-developer-mcp",
  "cloudflare.com": "https://github.com/cloudflare/mcp-server-cloudflare",
  "shopify.com": "https://github.com/Shopify/dev-mcp",
  "sentry.io": "https://github.com/getsentry/sentry-mcp",
}

const MCP_PATHS = [
  "/.well-known/mcp.json", "/.well-known/ai-plugin.json",
  "/mcp", "/mcp.json", "/api/mcp", "/v1/mcp", "/.well-known/mcp",
]

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }

function isValidSpec(data: unknown): data is Record<string, unknown> {
  return !!data && typeof data === "object" &&
    ("openapi" in (data as object) || "swagger" in (data as object) || "paths" in (data as object))
}

async function fetchJson(url: string): Promise<Record<string, unknown> | null> {
  try {
    const res = await fetchWithTimeout(url, { headers: HEADERS })
    if (!res.ok) return null
    const data = await res.json().catch(() => null)
    return isValidSpec(data) ? (data as Record<string, unknown>) : null
  } catch { return null }
}

async function checkMcpServer(baseUrl: string, homepageHtml: string): Promise<Phase1Result> {
  const hostname = new URL(baseUrl).hostname.replace(/^www\./, "")

  const knownUrl = KNOWN_MCP_SERVERS[hostname]
  if (knownUrl) return { status: "FOUND", evidence: knownUrl }

  for (const path of MCP_PATHS) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok) return { status: "FOUND", evidence: `${baseUrl}${path}` }
    } catch { /* continue */ }
  }

  try {
    const nameQuery = hostname.split(".")[0]
    const res = await fetchWithTimeout(
      `https://registry.smithery.ai/servers?q=${encodeURIComponent(nameQuery)}&pageSize=5`,
      { headers: { ...HEADERS, "Accept": "application/json" } }
    )
    if (res.ok) {
      const data = await res.json()
      const servers: Array<{ homepage?: string; qualifiedName?: string }> = data?.servers ?? data ?? []
      if (Array.isArray(servers)) {
        const exact = servers.find(s => s.homepage?.includes(hostname))
        if (exact) return { status: "FOUND", evidence: exact.homepage ?? "smithery.ai registry" }
        const loose = servers.find(s => s.qualifiedName?.toLowerCase().includes(nameQuery))
        if (loose) return { status: "UNCERTAIN", evidence: "possible match in smithery.ai registry" }
      }
    }
  } catch { /* continue */ }

  try {
    const nameQuery = hostname.split(".")[0]
    const res = await fetchWithTimeout(
      `https://mcp.so/api/search?q=${encodeURIComponent(nameQuery)}`,
      { headers: HEADERS }
    )
    if (res.ok) {
      const data = await res.json()
      if (Array.isArray(data) && data.length > 0) {
        const exact = data.find((s: { homepage?: string }) => s.homepage?.includes(hostname))
        if (exact) return { status: "FOUND", evidence: exact.homepage ?? "mcp.so registry" }
        return { status: "UNCERTAIN", evidence: "possible match in mcp.so registry" }
      }
    }
  } catch { /* continue */ }

  if (/model.context.protocol|mcp.server|\.well-known\/mcp|mcp\.json/i.test(homepageHtml)) {
    return { status: "UNCERTAIN", evidence: "MCP mentioned on homepage" }
  }

  return { status: "NOT_FOUND" }
}

async function checkOpenApiSpec(baseUrl: string): Promise<Phase1Result> {
  const hostname = new URL(baseUrl).hostname.replace(/^www\./, "")

  const knownUrl = KNOWN_OPENAPI_SPECS[hostname]
  if (knownUrl) {
    const data = await fetchJson(knownUrl)
    if (data) {
      const hasPaths = "paths" in data && data.paths && typeof data.paths === "object" && Object.keys(data.paths).length > 0
      return hasPaths
        ? { status: "FOUND", evidence: knownUrl, rawData: data }
        : { status: "UNCERTAIN", evidence: knownUrl, rawData: data }
    }
  }

  const origins = [baseUrl, `https://api.${hostname}`, `https://developer.${hostname}`]
  const urlsToProbe = origins.flatMap(origin => OPENAPI_PATHS.map(path => `${origin}${path}`))

  const results = await Promise.allSettled(urlsToProbe.map(url => fetchJson(url).then(d => d ? { url, data: d } : null)))
  for (const r of results) {
    if (r.status !== "fulfilled" || !r.value) continue
    const { url, data } = r.value
    const hasPaths = "paths" in data && data.paths && typeof data.paths === "object" && Object.keys(data.paths).length > 0
    return hasPaths
      ? { status: "FOUND", evidence: url, rawData: data }
      : { status: "UNCERTAIN", evidence: url, rawData: data }
  }

  const docPages = ["/docs", "/developer", "/api", "/api-docs", "/developers"]
  const specLinkPattern = /href=["']([^"']*(?:openapi|swagger)[^"']*\.(?:json|yaml))["']/gi
  for (const page of docPages) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${page}`, { headers: HEADERS })
      if (!res.ok) continue
      const html = await res.text()
      const matches = [...html.matchAll(specLinkPattern)]
      for (const match of matches) {
        const href = match[1]
        const specUrl = href.startsWith("http") ? href : `${baseUrl}${href.startsWith("/") ? "" : "/"}${href}`
        const data = await fetchJson(specUrl)
        if (data) {
          const hasPaths = "paths" in data && data.paths && typeof data.paths === "object" && Object.keys(data.paths).length > 0
          return hasPaths
            ? { status: "FOUND", evidence: specUrl, rawData: data }
            : { status: "UNCERTAIN", evidence: specUrl, rawData: data }
        }
      }
    } catch { /* continue */ }
  }

  return { status: "NOT_FOUND" }
}

function checkPublicApi(homepageHtml: string, robotsTxt: string): Phase1Result {
  let signals = 0
  const hasApiHref = /href=["'][^"']*\/(developers|api|docs)[^"']*["']/i.test(homepageHtml)
  if (hasApiHref) signals++
  // Strip anchor tags before checking for bare keyword mentions to avoid double-counting link text
  const htmlWithoutAnchors = homepageHtml.replace(/<a\b[^>]*>[\s\S]*?<\/a>/gi, "")
  if (/\b(API|Developers|Documentation)\b/.test(htmlWithoutAnchors)) signals++
  if (/rel=["']api["']/i.test(homepageHtml)) signals++
  if (/^(?:Allow|Disallow):\s*\/api\//im.test(robotsTxt)) signals++

  if (signals >= 2) return { status: "FOUND", evidence: `${signals} API signals in homepage/robots.txt` }
  if (signals === 1) return { status: "UNCERTAIN", evidence: "1 weak API signal found" }
  return { status: "NOT_FOUND" }
}

export function computeApiCoverage(spec: Record<string, unknown> | undefined): { percentage: number | null } {
  if (!spec || !("paths" in spec) || !spec.paths || typeof spec.paths !== "object") {
    return { percentage: null }
  }
  const paths = spec.paths as Record<string, Record<string, { description?: string; summary?: string }>>
  const httpMethods = ["get", "post", "put", "patch", "delete", "head", "options"]
  let total = 0, documented = 0
  for (const pathItem of Object.values(paths)) {
    if (!pathItem || typeof pathItem !== "object") continue
    for (const method of httpMethods) {
      const op = pathItem[method]
      if (!op) continue
      total++
      if (op.description?.trim() || op.summary?.trim()) documented++
    }
  }
  if (total === 0) return { percentage: 0 }
  return { percentage: Math.round((documented / total) * 100) }
}

export async function checkMachineInterfacePhase1(
  baseUrl: string,
  homepageHtml: string
): Promise<MachineInterfacePhase1Results> {
  let robotsTxt = ""
  try {
    const res = await fetchWithTimeout(`${baseUrl}/robots.txt`, { headers: HEADERS })
    if (res.ok) robotsTxt = await res.text()
  } catch { /* proceed */ }

  const [mcpRes, openApiRes] = await Promise.allSettled([
    checkMcpServer(baseUrl, homepageHtml),
    checkOpenApiSpec(baseUrl),
  ])

  return {
    mcpServer: mcpRes.status === "fulfilled" ? mcpRes.value : { status: "NOT_FOUND" },
    openApiSpec: openApiRes.status === "fulfilled" ? openApiRes.value : { status: "NOT_FOUND" },
    publicApiExists: checkPublicApi(homepageHtml, robotsTxt),
  }
}
