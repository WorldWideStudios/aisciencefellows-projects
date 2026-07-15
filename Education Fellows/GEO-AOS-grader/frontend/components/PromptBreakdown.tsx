"use client";

import { useState } from "react";

import { SENTIMENT_LABEL } from "@/lib/score";
import type { PromptResultOut, ReportOut } from "@/lib/types";

interface Props {
  report: ReportOut;
}

function escapeRegex(s: string): string {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlight(text: string, brandAliases: string[], competitorNames: string[]): React.ReactNode[] {
  if (!text) return [text];
  const brand = brandAliases.filter(Boolean).sort((a, b) => b.length - a.length);
  const comp = competitorNames.filter(Boolean).sort((a, b) => b.length - a.length);
  if (brand.length === 0 && comp.length === 0) return [text];

  const brandPattern = brand.map(escapeRegex).join("|");
  const compPattern = comp.map(escapeRegex).join("|");
  const combined = [brandPattern, compPattern].filter(Boolean).join("|");
  const re = new RegExp(`(${combined})`, "giu");
  const parts = text.split(re);

  return parts.map((part, idx) => {
    if (!part) return null;
    const lower = part.toLowerCase();
    if (brand.some((b) => b.toLowerCase() === lower)) {
      return (
        <mark key={idx} className="rounded bg-green-100 px-0.5 text-green-900">
          {part}
        </mark>
      );
    }
    if (comp.some((c) => c.toLowerCase() === lower)) {
      return (
        <mark key={idx} className="rounded bg-blue-100 px-0.5 text-blue-900">
          {part}
        </mark>
      );
    }
    return <span key={idx}>{part}</span>;
  });
}

export default function PromptBreakdown({ report }: Props) {
  const [openId, setOpenId] = useState<string | null>(null);
  const competitorNames = (report.competitors ?? []).map((c) => c.name);
  const brandAliases = report.brand_aliases ?? [];

  return (
    <section>
      <h2 className="mb-3 text-xl font-semibold">Breakdown by query</h2>
      <div className="overflow-hidden rounded-xl border border-neutral-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-neutral-50 text-xs uppercase tracking-wide text-neutral-500">
            <tr>
              <th className="px-4 py-3">Query</th>
              <th className="px-3 py-3 text-center">Cited</th>
              <th className="px-3 py-3 text-center">Mentioned</th>
              <th className="px-3 py-3">Sentiment</th>
              <th className="px-3 py-3">Competitors</th>
            </tr>
          </thead>
          <tbody>
            {report.prompt_results.map((pr) => {
              const expanded = openId === pr.id;
              return (
                <ExpandableRow
                  key={pr.id}
                  pr={pr}
                  expanded={expanded}
                  onToggle={() => setOpenId(expanded ? null : pr.id)}
                  brandAliases={brandAliases}
                  competitorNames={competitorNames}
                />
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

interface RowProps {
  pr: PromptResultOut;
  expanded: boolean;
  onToggle: () => void;
  brandAliases: string[];
  competitorNames: string[];
}

function ExpandableRow({ pr, expanded, onToggle, brandAliases, competitorNames }: RowProps) {
  return (
    <>
      <tr
        className="cursor-pointer border-t border-neutral-100 hover:bg-neutral-50"
        onClick={onToggle}
      >
        <td className="px-4 py-3">
          <div className="flex items-center gap-2">
            <span className={`text-neutral-400 transition ${expanded ? "rotate-90" : ""}`}>▸</span>
            <span className="text-neutral-900">{pr.prompt}</span>
          </div>
        </td>
        <td className="px-3 py-3 text-center">{pr.brand_cited ? "✓" : "—"}</td>
        <td className="px-3 py-3 text-center">{pr.brand_mentioned ? "✓" : "—"}</td>
        <td className="px-3 py-3 text-neutral-600">
          {pr.sentiment ? SENTIMENT_LABEL[pr.sentiment] : "—"}
        </td>
        <td className="px-3 py-3 text-neutral-600">
          {pr.competitors_mentioned.length > 0 ? pr.competitors_mentioned.join(", ") : "—"}
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-neutral-100 bg-neutral-50">
          <td colSpan={5} className="px-4 py-5">
            {pr.error ? (
              <p className="text-sm text-red-600">Error: {pr.error}</p>
            ) : (
              <div className="space-y-4">
                <div>
                  <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
                    Perplexity response
                  </p>
                  <div className="max-h-96 overflow-y-auto whitespace-pre-wrap rounded-lg bg-white p-4 text-sm leading-relaxed text-neutral-800 ring-1 ring-neutral-200">
                    {highlight(pr.raw_response, brandAliases, competitorNames)}
                  </div>
                </div>
                {pr.citations.length > 0 && (
                  <div>
                    <p className="mb-2 text-xs font-medium uppercase tracking-wide text-neutral-500">
                      Sources ({pr.citations.length})
                    </p>
                    <ul className="flex flex-wrap gap-2">
                      {pr.citations.map((c, idx) => (
                        <li key={idx}>
                          <a
                            href={`https://${c}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-block rounded-full bg-white px-3 py-1 text-xs text-neutral-700 ring-1 ring-neutral-200 hover:ring-neutral-400"
                          >
                            {c}
                          </a>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  );
}
