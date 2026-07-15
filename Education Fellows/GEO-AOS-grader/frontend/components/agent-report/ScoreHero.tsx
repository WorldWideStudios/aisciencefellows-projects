interface Props {
  domain: string
  totalScore: number
  grade: string
  gradeColor: string
  scannedAt: string
}

export default function ScoreHero({ domain, totalScore, grade, gradeColor, scannedAt }: Props) {
  return (
    <section className="rounded-2xl border border-neutral-200 bg-neutral-50 px-6 py-10 sm:px-10 sm:py-14">
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-neutral-500">Agent Operability Score</p>
          <div className="mt-2 flex items-baseline gap-3">
            <span className="text-7xl font-semibold tracking-tight sm:text-8xl" style={{ color: gradeColor }}>
              {totalScore}
            </span>
            <span className="text-2xl text-neutral-400">/ 100</span>
          </div>
          <p className="mt-2 text-sm text-neutral-500">{domain}</p>
        </div>
        <div className="text-left sm:text-right">
          <span
            className="inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ring-1 ring-inset"
            style={{
              color: gradeColor,
              borderColor: gradeColor + "55",
              backgroundColor: gradeColor + "15",
            }}
          >
            {grade}
          </span>
          <p className="mt-3 text-xs text-neutral-400">
            Scanned {new Date(scannedAt).toLocaleDateString("en-GB")}
          </p>
        </div>
      </div>
    </section>
  )
}
