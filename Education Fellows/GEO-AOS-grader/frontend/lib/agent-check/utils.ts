import { Redis } from "@upstash/redis"
import type { AgentCheckResponse } from "./types"
export { normalizeUrl } from "./url-utils"

export async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs = 8000
): Promise<Response> {
  const controller = new AbortController()
  const id = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...options, signal: controller.signal })
  } finally {
    clearTimeout(id)
  }
}

const rateLimitMap = new Map<string, number[]>()

export function checkRateLimit(ip: string, maxPerHour = 10): boolean {
  const now = Date.now()
  const windowMs = 60 * 60 * 1000
  const timestamps = (rateLimitMap.get(ip) ?? []).filter(t => now - t < windowMs)
  if (timestamps.length >= maxPerHour) return false
  rateLimitMap.set(ip, [...timestamps, now])
  return true
}

// ── OpenRouter ────────────────────────────────────────────────────────────────

export async function callOpenRouter(
  model: string,
  prompt: string,
  maxTokens = 500
): Promise<string> {
  const apiKey = process.env.OPENROUTER_API_KEY
  if (!apiKey) throw new Error("OPENROUTER_API_KEY not set")

  const res = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      model,
      messages: [{ role: "user", content: prompt }],
      max_tokens: maxTokens,
      response_format: { type: "json_object" },
    }),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new Error(`OpenRouter ${res.status}: ${text}`)
  }

  let data: unknown
  try {
    data = await res.json()
  } catch {
    throw new Error(`OpenRouter ${res.status}: invalid JSON response`)
  }
  const content = (data as { choices?: Array<{ message?: { content?: unknown } }> })?.choices?.[0]?.message?.content
  if (typeof content !== "string") throw new Error("OpenRouter returned unexpected response shape")
  return content
}

// ── Upstash Redis cache ───────────────────────────────────────────────────────

let _redis: Redis | null = null

function getRedis(): Redis | null {
  if (_redis) return _redis
  if (!process.env.UPSTASH_REDIS_REST_URL || !process.env.UPSTASH_REDIS_REST_TOKEN) return null
  _redis = new Redis({
    url: process.env.UPSTASH_REDIS_REST_URL,
    token: process.env.UPSTASH_REDIS_REST_TOKEN,
  })
  return _redis
}

export function resetRedis(): void {
  _redis = null
}

export async function getCachedResult(domain: string): Promise<AgentCheckResponse | null> {
  const r = getRedis()
  if (!r) return null
  try {
    return await r.get<AgentCheckResponse>(`agent-check:${domain}`)
  } catch { return null }
}

export async function setCachedResult(domain: string, result: AgentCheckResponse): Promise<void> {
  const r = getRedis()
  if (!r) return
  try {
    await r.set(`agent-check:${domain}`, result, { ex: 86400 })
  } catch { /* ignore cache write failures */ }
}
