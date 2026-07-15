"use client"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { normalizeUrl } from "@/lib/agent-check/url-utils"

export default function AgentReportForm() {
  const router = useRouter()
  const [url, setUrl] = useState("")
  const [error, setError] = useState<string | null>(null)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const { domain } = normalizeUrl(url.trim())
      router.push(`/agent-report/${encodeURIComponent(domain)}`)
    } catch {
      setError("Enter a valid URL — e.g. stripe.com")
    }
  }

  return (
    <form onSubmit={onSubmit} className="w-full space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="stripe.com or https://stripe.com"
          className="flex-1 border border-ink/20 bg-transparent px-4 py-3 text-base text-ink placeholder:text-ink/40 outline-none focus:border-ink transition-colors"
          required
        />
        <button
          type="submit"
          disabled={!url.trim()}
          className="bg-ink px-6 py-3 text-sm font-medium text-cream transition-colors hover:bg-orange disabled:cursor-not-allowed disabled:opacity-50"
        >
          Run scan
        </button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink/45">
        Scan takes ~30 seconds.
      </p>
    </form>
  )
}
