import { type NextRequest } from "next/server"
import { checkRateLimit, normalizeUrl } from "@/lib/agent-check/utils"
import { runAgentCheck } from "@/lib/agent-check/index"
import type { SSEEvent } from "@/lib/agent-check/types"

export const dynamic = "force-dynamic"

export async function POST(req: NextRequest) {
  let body: { url?: string }
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "Invalid JSON body" }, { status: 400 })
  }

  if (!body.url || typeof body.url !== "string") {
    return Response.json({ error: "url is required" }, { status: 400 })
  }

  let normalized: { url: string; domain: string }
  try {
    normalized = normalizeUrl(body.url)
  } catch {
    return Response.json({ error: "Invalid URL" }, { status: 400 })
  }

  const ip =
    req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ??
    req.headers.get("x-real-ip") ??
    "unknown"

  if (!checkRateLimit(ip)) {
    return Response.json({ error: "Rate limit exceeded. Max 10 scans per hour." }, { status: 429 })
  }

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    async start(controller) {
      function send(event: SSEEvent) {
        try {
          controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`))
        } catch { /* client disconnected */ }
      }

      try {
        await runAgentCheck(normalized.url, normalized.domain, send)
      } catch (err) {
        send({ type: "error", message: err instanceof Error ? err.message : "Scan failed" })
      } finally {
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      "Connection": "keep-alive",
      "X-Accel-Buffering": "no",
    },
  })
}
