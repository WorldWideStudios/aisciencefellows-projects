import { fetchWithTimeout, callOpenRouter } from "./utils"
import type { Phase2CheckName, RouterOutput } from "./types"

const HEADERS = { "User-Agent": `AgentReadinessBot/1.0` }
const DOC_SUBDOMAIN = /^https?:\/\/(docs|developer|api|dev)\./
const KEYWORD_HREF = /docs|api|developer|sdk|library|reference/i
const SITEMAP_KEYWORD = /doc|api|sdk|developer|reference/i
const FALLBACK_PATHS = ["/docs", "/developers", "/api", "/about"]

const HARDCODED_PATHS: Record<Phase2CheckName, string[]> = {
  mcpServer:        ["/developers", "/docs", "/platform"],
  openApiSpec:      ["/developers", "/docs", "/api", "/platform", "/build"],
  publicApiExists:  ["/developers", "/docs"],
  schemaOrg:        ["/about", "/product", "/features", "/platform"],
  sdkDocs:          ["/developers", "/docs", "/build", "/platform"],
  oauth:            ["/docs/authentication", "/docs/auth", "/developers", "/security"],
  apiKeySupport:    ["/docs/authentication", "/developers", "/api"],
}

export function isSafeUrl(url: string): boolean {
  try {
    const u = new URL(url)
    if (u.protocol !== "https:" && u.protocol !== "http:") return false
    const h = u.hostname.toLowerCase()
    if (h === "localhost" || h === "127.0.0.1" || h === "::1") return false
    // Block private IPv4 ranges
    const ipv4 = h.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/)
    if (ipv4) {
      const [, a, b] = ipv4.map(Number)
      if (a === 10) return false
      if (a === 172 && b >= 16 && b <= 31) return false
      if (a === 192 && b === 168) return false
    }
    return true
  } catch { return false }
}

function resolveHref(href: string, baseUrl: string): string | null {
  try { return new URL(href, baseUrl).href } catch { return null }
}

function isSameDomainOrDocSubdomain(href: string, hostname: string): boolean {
  try {
    const u = new URL(href)
    const base = hostname.replace(/^www\./, "")
    if (u.hostname === hostname || u.hostname === `www.${base}` || u.hostname === base) return true
    if (u.hostname.endsWith(`.${base}`) && DOC_SUBDOMAIN.test(href)) return true
    return false
  } catch { return false }
}

export function extractNavLinks(html: string, baseUrl: string): string[] {
  const hostname = new URL(baseUrl).hostname
  const candidates = new Set<string>()

  // Links inside structural elements
  const structureRe = /<(?:nav|header|footer)[^>]*>([\s\S]*?)<\/(?:nav|header|footer)>/gi
  let m: RegExpExecArray | null
  while ((m = structureRe.exec(html)) !== null) {
    const block = m[1]
    const hrefRe = /href=["']([^"'#?][^"']*)["']/gi
    let h: RegExpExecArray | null
    while ((h = hrefRe.exec(block)) !== null) {
      const abs = resolveHref(h[1], baseUrl)
      if (abs && isSameDomainOrDocSubdomain(abs, hostname)) candidates.add(abs)
    }
  }

  // Keyword-bearing links anywhere in the page
  const allHrefRe = /href=["']([^"'#?][^"']*)["']/gi
  while ((m = allHrefRe.exec(html)) !== null) {
    if (!KEYWORD_HREF.test(m[1])) continue
    const abs = resolveHref(m[1], baseUrl)
    if (abs && isSameDomainOrDocSubdomain(abs, hostname)) candidates.add(abs)
  }

  return [...candidates].slice(0, 25)
}

async function fetchSitemapCandidates(baseUrl: string): Promise<string[]> {
  const candidates: string[] = []
  try {
    let sitemapUrl = `${baseUrl}/sitemap.xml`
    try {
      const robotsRes = await fetchWithTimeout(`${baseUrl}/robots.txt`, { headers: HEADERS }, 5000)
      if (robotsRes.ok) {
        const txt = await robotsRes.text()
        const match = /^Sitemap:\s*(.+)$/mi.exec(txt)
        if (match) sitemapUrl = match[1].trim()
      }
    } catch { /* use default sitemap URL */ }

    const sitemapRes = await fetchWithTimeout(sitemapUrl, { headers: HEADERS }, 5000)
    if (!sitemapRes.ok) return candidates
    const xml = await sitemapRes.text()
    const locRe = /<loc>([^<]+)<\/loc>/gi
    let m: RegExpExecArray | null
    while ((m = locRe.exec(xml)) !== null && candidates.length < 20) {
      const url = m[1].trim()
      if (SITEMAP_KEYWORD.test(url)) candidates.push(url)
    }
  } catch { /* sitemap unavailable */ }
  return candidates
}

export async function buildCandidates(html: string, baseUrl: string): Promise<string[]> {
  const [navLinks, sitemapLinks] = await Promise.all([
    Promise.resolve(extractNavLinks(html, baseUrl)),
    fetchSitemapCandidates(baseUrl),
  ])
  const seen = new Set<string>()
  const all: string[] = []
  for (const url of [...navLinks, ...sitemapLinks]) {
    if (!seen.has(url)) { seen.add(url); all.push(url) }
  }
  if (all.length < 3) {
    for (const path of FALLBACK_PATHS) {
      const url = new URL(path, baseUrl).href
      if (!seen.has(url)) { seen.add(url); all.push(url) }
    }
  }
  return all.slice(0, 35)
}

export async function fetchPagesForUrls(urls: string[]): Promise<string> {
  const parts: string[] = []
  for (const url of urls.slice(0, 3).filter(isSafeUrl)) {
    try {
      const res = await fetchWithTimeout(url, { headers: HEADERS }, 8000)
      if (res.ok) {
        const text = await res.text()
        parts.push(`--- ${url} ---\n${text.slice(0, 2000)}`)
      }
    } catch { /* skip */ }
  }
  return parts.join("\n\n")
}

const SONNET = "anthropic/claude-sonnet-4-5"

interface SonnetRouterRaw {
  platformHint: string
  pages: Partial<Record<Phase2CheckName, string[]>>
  taskHints: Partial<Record<Phase2CheckName, string>>
}

function buildRouterPrompt(domain: string, title: string, description: string, candidates: string[]): string {
  return `You are a routing agent for an AI agent operability checker. Your job is to identify the best pages to fetch for each check type.

DOMAIN: ${domain}
PAGE TITLE: ${title}
META DESCRIPTION: ${description}

DISCOVERED CANDIDATE URLs:
${candidates.map((u, i) => `${i + 1}. ${u}`).join("\n")}

For each check type, return the 3 best URLs to fetch. You may use URLs from the candidate list OR URLs from your world knowledge if the candidate list is missing something important. Also return a one-line task hint if you have specific knowledge about this platform.

Check types:
- mcpServer: find an official MCP (Model Context Protocol) server
- openApiSpec: find an OpenAPI/Swagger machine-readable spec file
- publicApiExists: find the developer portal or API documentation
- schemaOrg: find pages with JSON-LD structured data
- sdkDocs: find SDK / client library documentation
- oauth: find OAuth 2.0 authentication documentation
- apiKeySupport: find API key / personal access token documentation

Return ONLY valid JSON (no markdown, no other text):
{
  "platformHint": "one-line platform description or empty string",
  "pages": {
    "mcpServer": ["url1", "url2", "url3"],
    "openApiSpec": ["url1", "url2", "url3"],
    "publicApiExists": ["url1", "url2", "url3"],
    "schemaOrg": ["url1", "url2", "url3"],
    "sdkDocs": ["url1", "url2", "url3"],
    "oauth": ["url1", "url2", "url3"],
    "apiKeySupport": ["url1", "url2", "url3"]
  },
  "taskHints": {
    "mcpServer": "specific hint or empty string",
    "openApiSpec": "specific hint or empty string",
    "publicApiExists": "specific hint or empty string",
    "schemaOrg": "specific hint or empty string",
    "sdkDocs": "specific hint or empty string",
    "oauth": "specific hint or empty string",
    "apiKeySupport": "specific hint or empty string"
  }
}`
}

export async function callSonnetRouter(
  domain: string,
  title: string,
  description: string,
  candidates: string[]
): Promise<SonnetRouterRaw> {
  const prompt = buildRouterPrompt(domain, title, description, candidates)
  const raw = await callOpenRouter(SONNET, prompt, 2000)
  const content = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim()
  const parsed = JSON.parse(content) as SonnetRouterRaw
  if (!parsed?.pages || typeof parsed.pages !== "object") throw new Error("Invalid router response")
  return parsed
}

export async function runPageRouter(
  url: string,
  domain: string,
  homepageHtml: string,
  needed: Set<Phase2CheckName>
): Promise<RouterOutput> {
  if (needed.size === 0) return { platformHint: "", pages: {}, taskHints: {} }

  try {
    const candidates = await buildCandidates(homepageHtml, url)
    const title = /<title[^>]*>([^<]*)<\/title>/i.exec(homepageHtml)?.[1]?.trim() ?? ""
    const metaDesc = /<meta[^>]+name=["']description["'][^>]+content=["']([^"']*)["']/i.exec(homepageHtml)?.[1]?.trim() ?? ""

    const routerResult = await callSonnetRouter(domain, title, metaDesc, candidates)

    const pageEntries = await Promise.all(
      [...needed].map(async name => {
        const urls = routerResult.pages[name] ?? []
        return [name, await fetchPagesForUrls(urls)] as [Phase2CheckName, string]
      })
    )

    return {
      platformHint: routerResult.platformHint ?? "",
      pages: Object.fromEntries(pageEntries),
      taskHints: routerResult.taskHints ?? {},
    }
  } catch {
    return buildFallbackOutput(url, needed)
  }
}

export async function buildFallbackOutput(baseUrl: string, needed: Set<Phase2CheckName>): Promise<RouterOutput> {
  const entries = await Promise.all(
    [...needed].map(async name => {
      const urls = HARDCODED_PATHS[name].map(p => new URL(p, baseUrl).href)
      return [name, await fetchPagesForUrls(urls)] as [Phase2CheckName, string]
    })
  )
  return {
    platformHint: "",
    pages: Object.fromEntries(entries),
    taskHints: Object.fromEntries([...needed].map(n => [n, ""])),
  }
}
