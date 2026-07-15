"use client"
import { use, useEffect, useRef, useState } from "react"
import type { AgentCheckResponse, SSEEvent } from "@/lib/agent-check/types"
import ScanProgress from "@/components/agent-report/ScanProgress"
import ReportLayout from "@/components/agent-report/ReportLayout"

interface Props {
  params: Promise<{ domain: string }>
}

export default function AgentReportDomainPage({ params }: Props) {
  const { domain } = use(params)
  const decodedDomain = decodeURIComponent(domain)

  const [completedBlocks, setCompletedBlocks] = useState<Set<string>>(new Set())
  const [result, setResult] = useState<AgentCheckResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const hasStarted = useRef(false)

  useEffect(() => {
    if (hasStarted.current) return
    hasStarted.current = true

    async function runScan() {
      try {
        const res = await fetch("/api/agent-check", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: `https://${decodedDomain}` }),
        })

        if (!res.ok) {
          const data = await res.json().catch(() => ({})) as { error?: string }
          setError(data.error ?? `HTTP ${res.status}`)
          return
        }

        const reader = res.body?.getReader()
        if (!reader) { setError("No response stream"); return }

        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          const chunks = buffer.split("\n\n")
          buffer = chunks.pop() ?? ""
          for (const chunk of chunks) {
            const line = chunk.trim()
            if (!line.startsWith("data: ")) continue
            try {
              const event = JSON.parse(line.slice(6)) as SSEEvent
              if (event.type === "block") {
                setCompletedBlocks(prev => new Set([...prev, event.block]))
              } else if (event.type === "complete") {
                setResult(event.result)
              } else if (event.type === "error") {
                setError(event.message)
              }
            } catch { /* malformed line, skip */ }
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Scan failed")
      }
    }

    runScan()
  }, [decodedDomain])

  if (error) {
    return (
      <main className="mx-auto max-w-3xl p-8">
        <p className="text-red-600">{error}</p>
        <a href="/agent-report" className="mt-4 inline-block text-sm underline hover:text-neutral-900">
          Try another site
        </a>
      </main>
    )
  }

  return (
    <main className="mx-auto max-w-3xl p-8">
      {result
        ? <ReportLayout result={result} />
        : <ScanProgress domain={decodedDomain} completedBlocks={completedBlocks} />
      }
    </main>
  )
}
