"use client"
import Link from "next/link"
import type { AgentCheckResponse } from "@/lib/agent-check/types"
import ScoreHero from "./ScoreHero"
import BlockCard from "./BlockCard"
import BlockDetail from "./BlockDetail"
import PendingBlock from "./PendingBlock"

const BLOCK_TITLES = {
  machineInterface:   "Machine Interface",
  browserOperability: "Browser Operability",
  agentDiscovery:     "Agent Discovery",
  authSecurity:       "Auth & Security",
} as const

interface Props {
  result: AgentCheckResponse
}

export default function ReportLayout({ result }: Props) {
  function copyLink() {
    navigator.clipboard.writeText(window.location.href).catch(() => {})
  }

  return (
    <div className="space-y-6">
      <ScoreHero
        domain={result.domain}
        totalScore={result.totalScore}
        grade={result.grade}
        gradeColor={result.gradeColor}
        scannedAt={result.scannedAt}
      />

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(Object.keys(BLOCK_TITLES) as Array<keyof typeof BLOCK_TITLES>).map(key => (
          <BlockCard
            key={key}
            title={BLOCK_TITLES[key]}
            score={result.blocks[key].score}
            maxScore={result.blocks[key].maxScore}
            isPending={"status" in result.blocks[key] && (result.blocks[key] as { status: string }).status === "pending"}
          />
        ))}
      </div>

      <BlockDetail title="Machine Interface"  block={result.blocks.machineInterface} />
      {result.blocks.browserOperability.status === "pending"
        ? <PendingBlock />
        : <BlockDetail title="Browser Operability" block={result.blocks.browserOperability} />}
      <BlockDetail title="Agent Discovery"    block={result.blocks.agentDiscovery} />
      <BlockDetail title="Auth & Security"    block={result.blocks.authSecurity} />

      <div className="flex flex-wrap gap-3 border-t border-neutral-200 pt-4 print-hide">
        <button
          onClick={copyLink}
          className="rounded-lg border border-neutral-300 px-4 py-2 text-sm text-neutral-700 transition hover:bg-neutral-50"
        >
          Share this report
        </button>
        <Link
          href="/agent-report"
          className="rounded-lg border border-neutral-300 px-4 py-2 text-sm text-neutral-700 transition hover:bg-neutral-50"
        >
          Scan another site
        </Link>
        <Link
          href="/"
          className="rounded-lg border border-neutral-300 px-4 py-2 text-sm text-neutral-700 transition hover:bg-neutral-50"
        >
          Check AI visibility →
        </Link>
      </div>
    </div>
  )
}
