export default function AgentReportLoading() {
  return (
    <main className="mx-auto max-w-3xl space-y-6 p-8">
      <div className="h-48 animate-pulse rounded-2xl bg-neutral-100" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-24 animate-pulse rounded-xl bg-neutral-100" />
        ))}
      </div>
      {Array.from({ length: 3 }).map((_, i) => (
        <div key={i} className="h-16 animate-pulse rounded-2xl bg-neutral-100" />
      ))}
    </main>
  )
}
