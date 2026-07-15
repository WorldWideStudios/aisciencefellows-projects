import { callOpenRouter } from "./utils"
import type { SubAgentResult } from "./types"

const HAIKU = "anthropic/claude-haiku-4-5"
const FALLBACK: SubAgentResult = { found: false, confidence: "low", evidence: "sub-agent error" }

function buildPrompt(domain: string, pages: string, task: string, taskHint: string): string {
  return `You are analyzing ${domain} for AI agent operability.

${pages ? `PAGES:\n${pages}` : "No pages available."}

TASK: ${task}${taskHint ? `\n\nPLATFORM HINT: ${taskHint}` : ""}

Return ONLY valid JSON with no other text:
{
  "found": boolean,
  "confidence": "high" | "medium" | "low",
  "evidence": "URL or quoted text where found, or empty string if not found",
  "details": "optional extra context"
}`
}

async function callAgent(prompt: string): Promise<SubAgentResult> {
  try {
    const raw = await callOpenRouter(HAIKU, prompt, 400)
    const content = raw.replace(/^```(?:json)?\s*/i, "").replace(/```\s*$/i, "").trim()
    const parsed = JSON.parse(content) as SubAgentResult
    if (typeof parsed.found !== "boolean" || !["high", "medium", "low"].includes(parsed.confidence)) {
      return FALLBACK
    }
    return parsed
  } catch { return FALLBACK }
}

export async function checkMcpServerAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Search for an official MCP (Model Context Protocol) server for ${domain}. Look for:
- Links or mentions of "MCP server", "model context protocol"
- A GitHub repository with "mcp" in the name alongside ${domain}
- Install instructions like "npx @modelcontextprotocol/" or similar
- Any reference to serving MCP protocol
Return the repository URL or install command as evidence.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkOpenApiSpecAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Find an OpenAPI or Swagger API specification for ${domain}. It may be linked from the pages provided. Look for:
- Links containing "openapi", "swagger", "api-spec", "api-docs", or "rest-api"
- File extensions .json or .yaml on spec-like paths
- Mentions of a machine-readable API specification URL
Return the direct URL to the spec file.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkPublicApiAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Determine if ${domain} offers a public API for programmatic access. Look in navigation, footer, and the pages provided for mentions of "API", "REST API", "GraphQL API", "developer platform", or links to API documentation. Return a URL to the API docs or developer portal.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkOAuthAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Find evidence that ${domain} supports OAuth 2.0 authentication. Look for text mentioning "OAuth 2.0", "OAuth2", "OpenID Connect", "authorization flow", or "access token" in the pages provided. Return a URL and a short quoted snippet as evidence.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkApiKeyAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Find evidence that ${domain} offers API keys or tokens for programmatic access. Look for "API key", "API token", "personal access token", "secret key", or "bearer token" in the pages provided. Return a URL and a short quoted snippet.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkSdkDocsAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Find evidence of a developer SDK for ${domain}. Look for links to npmjs.com, pypi.org, or GitHub alongside the word "SDK", or text like "npm install", "pip install", "client library" in the pages provided. Return the URL and package name if found.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}

export async function checkSchemaOrgAgent(domain: string, pages: string, taskHint: string): Promise<SubAgentResult> {
  const task = `Check the pages provided for JSON-LD structured data (inside <script type="application/ld+json"> tags). Look for @type values: SoftwareApplication, WebAPI, APIReference, Service, Action, or EntryPoint. Return the @type found and the page URL.`
  return callAgent(buildPrompt(domain, pages, task, taskHint))
}
