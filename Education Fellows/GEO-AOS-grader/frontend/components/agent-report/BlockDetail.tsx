"use client"
import { useState } from "react"
import type { BlockResult } from "@/lib/agent-check/types"
import CheckItem from "./CheckItem"

const CHECK_LABELS: Record<string, string> = {
  mcpServer:              "MCP Server",
  openApiSpec:            "OpenAPI Specification",
  apiDescriptionCoverage: "API Description Coverage",
  publicApiExists:        "Public API",
  llmsTxt:                "llms.txt Quality",
  robotsTxtAi:            "Robots.txt AI Permissions",
  schemaOrg:              "Schema.org Markup",
  sdkDocs:                "SDK Documentation",
  oauth:                  "OAuth 2.0 Support",
  apiKeySupport:          "API Key / Token Support",
  corsPolicy:             "CORS Policy",
  botBlocking:            "Bot Blocking",
  navigationWorking:      "Navigation Working",
  formsInteractable:      "Forms Interactable",
  authFlowReachable:      "Auth Flow Reachable",
  noJsWall:               "No JS Wall",
}

interface Props {
  title: string
  block: BlockResult
}

export default function BlockDetail({ title, block }: Props) {
  const [open, setOpen] = useState(true)

  return (
    <section className="rounded-2xl border border-neutral-200 bg-white">
      <button
        onClick={() => setOpen(o => !o)}
        className="flex w-full items-center justify-between px-6 py-4 text-left"
        aria-expanded={open}
      >
        <span className="font-semibold text-neutral-900">{title}</span>
        <span className="text-xs text-neutral-400">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="border-t border-neutral-100 px-6 py-2">
          {Object.entries(block.checks).map(([key, result]) => (
            <CheckItem key={key} name={CHECK_LABELS[key] ?? key} result={result} />
          ))}
          {Object.keys(block.checks).length === 0 && (
            <p className="py-4 text-sm text-neutral-400">No checks ran for this block.</p>
          )}
        </div>
      )}
    </section>
  )
}
