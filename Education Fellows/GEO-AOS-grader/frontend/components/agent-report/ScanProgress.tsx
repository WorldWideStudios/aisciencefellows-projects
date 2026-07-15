const STEPS = [
  { key: "machineInterface",   label: "Checking machine interfaces" },
  { key: "browserOperability", label: "Browser operability (stub)" },
  { key: "agentDiscovery",     label: "Analyzing agent discovery" },
  { key: "authSecurity",       label: "Testing auth & security" },
] as const

interface Props {
  domain: string
  completedBlocks: Set<string>
}

export default function ScanProgress({ domain, completedBlocks }: Props) {
  return (
    <div className="space-y-8 py-12">
      <p className="text-xl font-medium text-neutral-700">Scanning {domain}…</p>
      <div className="space-y-4">
        {STEPS.map(step => {
          const done = completedBlocks.has(step.key)
          return (
            <div key={step.key} className="flex items-center gap-3">
              <span className={`text-base ${done ? "text-green-500" : "text-neutral-300"}`}>
                {done ? "●" : "○"}
              </span>
              <span className={`text-sm ${done ? "text-neutral-900" : "text-neutral-400"}`}>
                {step.label}
              </span>
              {done && <span className="ml-auto text-xs text-green-600">done</span>}
            </div>
          )
        })}
      </div>
    </div>
  )
}
