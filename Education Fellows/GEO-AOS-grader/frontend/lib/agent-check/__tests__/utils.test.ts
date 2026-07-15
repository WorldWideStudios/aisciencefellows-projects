import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { normalizeUrl, checkRateLimit, callOpenRouter, getCachedResult, setCachedResult, resetRedis } from "../utils"

describe("normalizeUrl", () => {
  it("adds https:// when no scheme given", () => {
    const { url, domain } = normalizeUrl("stripe.com")
    expect(url).toBe("https://stripe.com")
    expect(domain).toBe("stripe.com")
  })

  it("strips www from domain", () => {
    const { domain } = normalizeUrl("https://www.github.com")
    expect(domain).toBe("github.com")
  })

  it("strips path, keeps origin only", () => {
    const { url } = normalizeUrl("https://stripe.com/docs/api")
    expect(url).toBe("https://stripe.com")
  })

  it("preserves https scheme", () => {
    const { url } = normalizeUrl("https://api.example.com")
    expect(url).toBe("https://api.example.com")
    expect(normalizeUrl("https://api.example.com").domain).toBe("example.com")
  })

  it("throws on clearly invalid input", () => {
    expect(() => normalizeUrl("not a url at all !!!")).toThrow()
  })
})

describe("checkRateLimit", () => {
  // Each test uses a unique IP to avoid cross-test state
  it("allows first request", () => {
    expect(checkRateLimit("1.1.1.1")).toBe(true)
  })

  it("blocks when limit exceeded", () => {
    const ip = "2.2.2.2"
    for (let i = 0; i < 10; i++) checkRateLimit(ip)
    expect(checkRateLimit(ip)).toBe(false)
  })

  it("allows up to the limit", () => {
    const ip = "3.3.3.3"
    for (let i = 0; i < 9; i++) checkRateLimit(ip)
    expect(checkRateLimit(ip)).toBe(true) // 10th request — allowed
  })
})

describe("callOpenRouter", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn())
    process.env.OPENROUTER_API_KEY = "test-key"
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    delete process.env.OPENROUTER_API_KEY
  })

  it("returns message content on success", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ choices: [{ message: { content: '{"found":true}' } }] }),
        { status: 200 }
      )
    )
    const result = await callOpenRouter("anthropic/claude-haiku-4-5", "test prompt", 300)
    expect(result).toBe('{"found":true}')
  })

  it("calls OpenRouter with Authorization header and json response_format", async () => {
    vi.mocked(fetch).mockResolvedValue(
      new Response(
        JSON.stringify({ choices: [{ message: { content: "{}" } }] }),
        { status: 200 }
      )
    )
    await callOpenRouter("anthropic/claude-haiku-4-5", "prompt")
    const [url, opts] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit]
    expect(url).toBe("https://openrouter.ai/api/v1/chat/completions")
    const body = JSON.parse(opts.body as string)
    expect(body.model).toBe("anthropic/claude-haiku-4-5")
    expect(body.response_format).toEqual({ type: "json_object" })
    expect((opts.headers as Record<string, string>)["Authorization"]).toBe("Bearer test-key")
  })

  it("throws when OPENROUTER_API_KEY is missing", async () => {
    delete process.env.OPENROUTER_API_KEY
    await expect(callOpenRouter("model", "prompt")).rejects.toThrow("OPENROUTER_API_KEY not set")
  })

  it("throws on non-200 response", async () => {
    vi.mocked(fetch).mockResolvedValue(new Response("Unauthorized", { status: 401 }))
    await expect(callOpenRouter("model", "prompt")).rejects.toThrow("OpenRouter 401")
  })
})

describe("cache functions (Redis not configured)", () => {
  beforeEach(() => {
    resetRedis()
    delete process.env.UPSTASH_REDIS_REST_URL
    delete process.env.UPSTASH_REDIS_REST_TOKEN
  })

  it("getCachedResult returns null when Redis not configured", async () => {
    const result = await getCachedResult("example.com")
    expect(result).toBeNull()
  })

  it("setCachedResult resolves without throwing when Redis not configured", async () => {
    const fakeResult = { domain: "example.com", scannedAt: "", totalScore: 0, grade: "", gradeColor: "", blocks: {} as never }
    await expect(setCachedResult("example.com", fakeResult)).resolves.toBeUndefined()
  })
})
