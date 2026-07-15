import type { CheckResult } from "@/lib/agent-check/types"

interface Props {
  name: string
  result: CheckResult
}

export default function CheckItem({ name, result }: Props) {
  const { score, maxScore, evidence, url } = result
  const full = score > 0 && score === maxScore
  const partial = score > 0 && score < maxScore
  const iconClass = full ? "text-green-500" : partial ? "text-yellow-500" : "text-red-400"
  const icon = full ? "✓" : partial ? "~" : "✗"

  return (
    <div className="flex items-start gap-3 border-b border-neutral-100 py-2.5 last:border-0">
      <span className={`mt-0.5 w-4 flex-shrink-0 text-sm font-semibold ${iconClass}`}>{icon}</span>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-neutral-800">{name}</p>
        {(evidence ?? url) && (
          <p className="mt-0.5 truncate text-xs text-neutral-500">{evidence ?? url}</p>
        )}
      </div>
      <span className="whitespace-nowrap text-xs text-neutral-500">
        {score} / {maxScore}
      </span>
    </div>
  )
}
