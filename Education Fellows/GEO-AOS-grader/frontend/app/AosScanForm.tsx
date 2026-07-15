"use client"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { normalizeUrl } from "@/lib/agent-check/url-utils"
import styles from "./AosScanForm.module.css"

export default function AosScanForm({ inputId = "scan-input" }: { inputId?: string }) {
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
    <div>
      <form className={styles.form} onSubmit={onSubmit} autoComplete="off">
        <input
          id={inputId}
          className={styles.input}
          type="text"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="stripe.com or https://stripe.com"
          spellCheck={false}
          aria-label="Platform URL to scan"
        />
        <button type="submit" className={styles.submit} disabled={!url.trim()}>
          Run scan
        </button>
      </form>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  )
}
