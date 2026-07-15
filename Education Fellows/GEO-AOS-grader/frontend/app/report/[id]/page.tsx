"use client";

import { use, useEffect, useState } from "react";

import ActionableInsights from "@/components/ActionableInsights";
import MetricCards from "@/components/MetricCards";
import Methodology from "@/components/Methodology";
import PromptBreakdown from "@/components/PromptBreakdown";
import ReportCTA from "@/components/ReportCTA";
import ScoreHero from "@/components/ScoreHero";
import SourceShareOfVoice from "@/components/SourceShareOfVoice";
import { getReport } from "@/lib/api";
import type { ReportOut } from "@/lib/types";

interface Props {
  params: Promise<{ id: string }>;
}

export default function ReportPage({ params }: Props) {
  const { id } = use(params);
  const [report, setReport] = useState<ReportOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | null = null;

    async function poll() {
      try {
        const fresh = await getReport(id);
        if (cancelled) return;
        setReport(fresh);
        if (fresh.status === "generating" || fresh.status === "analyzing" || fresh.status === "awaiting_confirmation") {
          timer = setTimeout(poll, 3000);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load");
      }
    }

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  if (error) {
    return (
      <main className="mx-auto max-w-2xl p-8">
        <h1 className="mb-3 text-2xl font-semibold">Error</h1>
        <p className="text-red-600">{error}</p>
      </main>
    );
  }

  if (!report) {
    return (
      <main className="mx-auto max-w-2xl p-8">
        <p className="text-neutral-500">Loading…</p>
      </main>
    );
  }

  if (report.status === "failed") {
    return (
      <main className="mx-auto max-w-2xl p-8">
        <h1 className="mb-3 text-2xl font-semibold">Something went wrong</h1>
        <p className="text-red-600">{report.error ?? "Unknown error"}</p>
      </main>
    );
  }

  if (report.status !== "completed") {
    return <Generating brandUrl={report.url} />;
  }

  return (
    <main className="mx-auto max-w-5xl space-y-10 p-6 sm:p-10">
      <header className="space-y-1">
        <p className="text-sm text-neutral-500">
          {report.brand_name ?? "Brand"} · {report.brand_domain ?? report.url}
        </p>
        {report.industry && <p className="text-xs text-neutral-400">{report.industry}</p>}
      </header>

      <ScoreHero report={report} />
      <MetricCards report={report} />
      <SourceShareOfVoice report={report} />
      <PromptBreakdown report={report} />
      <ActionableInsights report={report} />
      <Methodology report={report} />
      <ReportCTA />

      <footer className="border-t border-neutral-200 pt-6 text-xs text-neutral-400">
        AEO Grader · report from {new Date(report.updated_at).toLocaleString("en-US")}
      </footer>
    </main>
  );
}

function Generating({ brandUrl }: { brandUrl: string }) {
  return (
    <main className="mx-auto max-w-2xl p-8">
      <div className="space-y-5">
        <h1 className="text-3xl font-semibold tracking-tight">Running 10 queries through Perplexity…</h1>
        <p className="text-neutral-600">
          Analyzing visibility of {brandUrl} in AI search. Usually takes 60–90 seconds.
        </p>
        <div className="h-1 w-full overflow-hidden rounded bg-neutral-200">
          <div className="h-full w-1/2 animate-pulse rounded bg-neutral-900" />
        </div>
        <ul className="space-y-2 text-sm text-neutral-500">
          <li>· Parallel run of 10 queries</li>
          <li>· Extracting citations and in-text mentions</li>
          <li>· Sentiment classification for brand mentions</li>
          <li>· Aggregating Source Share of Voice</li>
        </ul>
      </div>
    </main>
  );
}
