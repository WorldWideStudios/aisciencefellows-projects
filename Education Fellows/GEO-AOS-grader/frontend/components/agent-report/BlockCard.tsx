interface Props {
  title: string
  score: number
  maxScore: number
  isPending?: boolean
}

export default function BlockCard({ title, score, maxScore, isPending = false }: Props) {
  const pct = maxScore > 0 ? Math.round((score / maxScore) * 100) : 0
  const barColor = pct >= 75 ? "#22c55e" : pct >= 40 ? "#eab308" : "#ef4444"

  return (
    <div className="rounded-xl border border-neutral-200 bg-white p-5">
      <p className="text-xs font-medium text-neutral-600">{title}</p>
      {isPending ? (
        <p className="mt-3 text-xs text-neutral-400">Coming soon</p>
      ) : (
        <>
          <p className="mt-2 text-2xl font-semibold text-neutral-900">
            {score}{" "}
            <span className="text-sm font-normal text-neutral-400">/ {maxScore}</span>
          </p>
          <div className="mt-3 h-1.5 w-full rounded-full bg-neutral-100">
            <div
              className="h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${pct}%`, backgroundColor: barColor }}
            />
          </div>
        </>
      )}
    </div>
  )
}
