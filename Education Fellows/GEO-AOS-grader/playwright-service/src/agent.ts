import OpenAI from "openai"
import type { ChatCompletionMessageParam } from "openai/resources"
import type { Page } from "playwright"
import { BROWSER_TOOLS, executeTool } from "./tools"
import type { AgentAssessment } from "./types"

const MODEL = "anthropic/claude-haiku-4-5"

export const FALLBACK_ASSESSMENT: AgentAssessment = {
  checks: {
    botBlocking:       { score: 0, maxScore: 6, found: false, evidence: "Scan failed" },
    navigationWorking: { score: 0, maxScore: 6, found: false, evidence: "Scan failed" },
    formsInteractable: { score: 0, maxScore: 5, found: false, evidence: "Scan failed" },
    authFlowReachable: { score: 0, maxScore: 4, found: false, evidence: "Scan failed" },
    noJsWall:          { score: 0, maxScore: 4, found: false, evidence: "Scan failed" },
  },
  blockers: ["Scan could not be completed"],
  sessionSummary: "Scan failed or timed out",
}

export const SYSTEM_PROMPT = `You are an AI agent testing whether a website can be operated by AI agents. Your job is to explore the site using the provided tools and assess how easy it is for an AI agent to navigate and interact with it.

Start by calling detect_blocking to check for bot-blocking, then navigate to the URL and explore. Try to:
1. Load the homepage and check if content is visible (noJsWall)
2. Navigate 2-3 internal links from the main navigation (navigationWorking)
3. Find and inspect any forms on the site (formsInteractable)
4. Find a login or sign-up page (authFlowReachable)

After your exploration, emit a JSON object as your final message (no other text, no markdown):
{
  "checks": {
    "botBlocking":       { "score": 0 or 6,  "maxScore": 6, "found": boolean, "evidence": "one sentence" },
    "navigationWorking": { "score": 0 or 6,  "maxScore": 6, "found": boolean, "evidence": "one sentence" },
    "formsInteractable": { "score": 0 or 5,  "maxScore": 5, "found": boolean, "evidence": "one sentence" },
    "authFlowReachable": { "score": 0 or 4,  "maxScore": 4, "found": boolean, "evidence": "one sentence" },
    "noJsWall":          { "score": 0 or 4,  "maxScore": 4, "found": boolean, "evidence": "one sentence" }
  },
  "blockers": ["plain-language description of each blocker, or empty array if none"],
  "sessionSummary": "one sentence summary of overall agent operability"
}

IMPORTANT scoring rules:
- botBlocking: found=true means blocking WAS detected (score=0). found=false means no blocking (score=6).
- All other checks: found=true means the capability works correctly (full score). found=false means it failed or was not found (score=0).`

// Extract the first balanced {...} JSON object from arbitrary text.
// The model often wraps its JSON in prose ("Here's my assessment:") and/or
// markdown fences, so we cannot assume the whole string is JSON. Scan for the
// first "{" and walk the string tracking brace depth (ignoring braces inside
// strings) until the matching "}" closes it.
function extractJsonObject(text: string): string | null {
  const start = text.indexOf("{")
  if (start === -1) return null
  let depth = 0
  let inString = false
  let escaped = false
  for (let i = start; i < text.length; i++) {
    const ch = text[i]
    if (inString) {
      if (escaped) escaped = false
      else if (ch === "\\") escaped = true
      else if (ch === '"') inString = false
      continue
    }
    if (ch === '"') inString = true
    else if (ch === "{") depth++
    else if (ch === "}") {
      depth--
      if (depth === 0) return text.slice(start, i + 1)
    }
  }
  return null
}

export function parseAssessment(text: string): AgentAssessment {
  try {
    const candidate = extractJsonObject(text)
    if (!candidate) return FALLBACK_ASSESSMENT
    const parsed = JSON.parse(candidate) as AgentAssessment
    if (!parsed?.checks || typeof parsed.checks !== "object") return FALLBACK_ASSESSMENT
    const required = ["botBlocking", "navigationWorking", "formsInteractable", "authFlowReachable", "noJsWall"] as const
    for (const key of required) {
      if (!parsed.checks[key] || typeof parsed.checks[key].score !== "number") return FALLBACK_ASSESSMENT
    }
    return parsed
  } catch {
    return FALLBACK_ASSESSMENT
  }
}

export async function runBrowserAgent(
  url: string,
  page: Page,
  client: OpenAI,
  maxTurns = 15
): Promise<AgentAssessment> {
  const messages: ChatCompletionMessageParam[] = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: `Scan this URL for AI agent operability: ${url}` },
  ]

  for (let turn = 0; turn < maxTurns; turn++) {
    const response = await client.chat.completions.create({
      model: MODEL,
      max_tokens: 1024,
      tools: BROWSER_TOOLS,
      messages,
    })

    const choice = response.choices[0]

    if (choice.finish_reason === "stop") {
      return parseAssessment(choice.message.content ?? "")
    }

    messages.push(choice.message)

    const toolCalls = choice.message.tool_calls ?? []
    if (toolCalls.length === 0) break

    const toolResults: ChatCompletionMessageParam[] = []
    for (const toolCall of toolCalls) {
      let input: Record<string, unknown> = {}
      try { input = JSON.parse(toolCall.function.arguments) as Record<string, unknown> } catch { /* use empty */ }
      const result = await executeTool(toolCall.function.name, input, page)
      toolResults.push({
        role: "tool",
        tool_call_id: toolCall.id,
        content: JSON.stringify(result),
      })
    }

    messages.push(...toolResults)
  }

  // Max turns reached — prompt for final JSON
  messages.push({ role: "user", content: "You have reached the maximum number of steps. Emit your final JSON assessment now, with no other text." })
  const final = await client.chat.completions.create({
    model: MODEL,
    max_tokens: 1024,
    messages,
  })
  return parseAssessment(final.choices[0].message.content ?? "")
}
