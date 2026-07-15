import type { Metadata } from "next"
import AgentReportForm from "./AgentReportForm"

export const metadata: Metadata = {
  title: "Agent Operability Report",
  description: "Find out if AI agents can actually work with your platform — not just find it.",
}

export default function AgentReportPage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col justify-center p-8">
      <div className="space-y-6">
        <header className="space-y-3">
          <h1 className="text-5xl font-semibold tracking-tight">Agent Operability Report</h1>
          <p className="max-w-xl text-lg text-neutral-600">
            Find out if AI agents can actually work with your platform — not just find it.
            We check for MCP servers, OpenAPI specs, OAuth support, and more.
          </p>
        </header>
        <AgentReportForm />
        <p className="text-sm text-neutral-500">
          Also check your AI visibility{" "}
          <a href="/" className="underline hover:text-neutral-900">
            with AEO Grader →
          </a>
        </p>
      </div>
    </main>
  )
}
