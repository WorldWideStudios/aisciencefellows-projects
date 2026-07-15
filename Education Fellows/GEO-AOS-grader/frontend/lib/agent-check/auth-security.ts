import { fetchWithTimeout } from "./utils"
import type { Phase1Result, AuthSecurityPhase1Results } from "./types"

const USER_AGENT = `AgentReadinessBot/1.0 (compatible; ${process.env.NEXT_PUBLIC_SITE_URL ?? ""}/agent-report)`
const HEADERS = { "User-Agent": USER_AGENT }
const API_KEY_PATTERN = /api\s*key|api\s*token|access\s+token|personal\s+access\s+token|secret\s+key/i

async function checkOAuth(baseUrl: string): Promise<Phase1Result> {
  for (const path of ["/.well-known/oauth-authorization-server", "/.well-known/openid-configuration"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok) {
        await res.json()
        return { status: "FOUND", evidence: `${baseUrl}${path}` }
      }
    } catch { /* continue */ }
  }
  for (const path of ["/developers", "/docs", "/api"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok) {
        const html = await res.text()
        if (/oauth\s*2\.?0|openid\s+connect/i.test(html)) {
          return { status: "UNCERTAIN", evidence: `OAuth 2.0 mentioned at ${baseUrl}${path}` }
        }
      }
    } catch { /* continue */ }
  }
  return { status: "NOT_FOUND" }
}

async function checkApiKeySupport(baseUrl: string): Promise<Phase1Result> {
  for (const path of ["/settings/api", "/account/api", "/api-keys"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok && API_KEY_PATTERN.test(await res.text())) {
        return { status: "FOUND", evidence: `${baseUrl}${path}` }
      }
    } catch { /* continue */ }
  }
  for (const path of ["/settings", "/account", "/developers", "/"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { headers: HEADERS })
      if (res.ok && API_KEY_PATTERN.test(await res.text())) {
        return { status: "UNCERTAIN", evidence: `API key mentioned at ${baseUrl}${path}` }
      }
    } catch { /* continue */ }
  }
  return { status: "NOT_FOUND" }
}

async function findApiEndpoint(baseUrl: string): Promise<string | undefined> {
  for (const path of ["/api/v1", "/api", "/api/v1/health", "/api/health"]) {
    try {
      const res = await fetchWithTimeout(`${baseUrl}${path}`, { method: "HEAD", headers: HEADERS })
      if (res.ok || res.status === 401 || res.status === 405) return `${baseUrl}${path}`
    } catch { /* continue */ }
  }
  return undefined
}

async function checkCors(baseUrl: string): Promise<Phase1Result> {
  const endpoint = await findApiEndpoint(baseUrl)
  if (!endpoint) return { status: "NOT_FOUND" }
  try {
    const res = await fetchWithTimeout(endpoint, {
      method: "OPTIONS",
      headers: { ...HEADERS, "Origin": "https://test.example.com", "Access-Control-Request-Method": "GET" },
    })
    const origin = res.headers.get("access-control-allow-origin")
    if (origin === "*") return { status: "FOUND", rawData: { policy: "*" } }
    if (origin) return { status: "UNCERTAIN", rawData: { policy: origin } }
    return { status: "UNCERTAIN", rawData: { policy: null } }
  } catch {
    return { status: "UNCERTAIN", rawData: { policy: null } }
  }
}

export async function checkAuthSecurityPhase1(
  baseUrl: string,
  _homepageHtml: string
): Promise<AuthSecurityPhase1Results> {
  const [oauthRes, apiKeyRes, corsRes] = await Promise.allSettled([
    checkOAuth(baseUrl),
    checkApiKeySupport(baseUrl),
    checkCors(baseUrl),
  ])

  return {
    oauth: oauthRes.status === "fulfilled" ? oauthRes.value : { status: "NOT_FOUND" },
    apiKeySupport: apiKeyRes.status === "fulfilled" ? apiKeyRes.value : { status: "NOT_FOUND" },
    corsPolicy: corsRes.status === "fulfilled" ? corsRes.value : { status: "NOT_FOUND" },
  }
}
