"use client";

import { useState } from "react";

import type { ReportOut } from "@/lib/types";

interface Props {
  report: ReportOut;
}

export default function Methodology({ report }: Props) {
  const [open, setOpen] = useState(false);
  const date = new Date(report.updated_at).toLocaleDateString("en-US", {
    day: "2-digit",
    month: "long",
    year: "numeric",
  });

  return (
    <section className="rounded-xl border border-neutral-200 bg-white">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between px-5 py-4 text-left"
      >
        <span className="text-base font-medium text-neutral-900">Methodology</span>
        <span className={`text-neutral-400 transition ${open ? "rotate-90" : ""}`}>▸</span>
      </button>
      {open && (
        <div className="space-y-5 border-t border-neutral-100 px-5 py-5 text-sm leading-relaxed text-neutral-700">
          <div>
            <p className="mb-2 font-medium text-neutral-900">Tool and date</p>
            <p>
              Model: <code className="rounded bg-neutral-100 px-1.5 py-0.5">perplexity/sonar-pro</code> via
              OpenRouter. Run date: {date}.
            </p>
          </div>

          <div>
            <p className="mb-2 font-medium text-neutral-900">Queries ({report.prompt_results.length})</p>
            <ol className="list-decimal space-y-1 pl-5">
              {report.prompt_results.map((p) => (
                <li key={p.id}>{p.prompt}</li>
              ))}
            </ol>
          </div>

          <div>
            <p className="mb-2 font-medium text-neutral-900">Score formula</p>
            <pre className="overflow-x-auto rounded-lg bg-neutral-50 p-3 text-xs">
{`base = (citation_rate * 0.6 + mention_rate * 0.4) * 100
penalty = 0.7 if sentiment = negative
        = 0.85 if sentiment = mixed
        = 1.0  otherwise
aeo_score = round(base * penalty, 1)`}
            </pre>
          </div>

          <div>
            <p className="mb-2 font-medium text-neutral-900">Sentiment</p>
            <p>
              For each query with a brand mention, a separate LLM call (gpt-4o-mini) classifies the tone:
              positive / neutral / negative. If both positive and negative are present, the result is mixed.
            </p>
          </div>

          <div>
            <p className="mb-2 font-medium text-neutral-900">Disclaimer</p>
            <p>
              Score is based on 10 queries × 1 run. Accuracy ±10 points due to the stochastic nature of AI responses.
              For trend monitoring, periodic runs are recommended.
            </p>
          </div>
        </div>
      )}
    </section>
  );
}
