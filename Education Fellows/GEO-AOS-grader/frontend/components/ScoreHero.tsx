import type { ReportOut } from "@/lib/types";
import { deltaToNextLevel, getLevel } from "@/lib/score";

interface Props {
  report: ReportOut;
}

function buildSummary(r: ReportOut): string {
  const brand = r.brand_name ?? "Brand";
  const total = r.prompt_results.length;
  const cited = r.prompt_results.filter((p) => p.brand_cited).length;
  const mentioned = r.prompt_results.filter((p) => p.brand_mentioned).length;

  const competitorDomains = new Set((r.competitors ?? []).map((c) => c.domain.toLowerCase()));
  const competitorTallies = new Map<string, { count: number; name: string }>();
  for (const c of r.competitors ?? []) competitorTallies.set(c.domain.toLowerCase(), { count: 0, name: c.name });
  for (const pr of r.prompt_results) {
    for (const d of pr.competitors_cited ?? []) {
      const key = d.toLowerCase();
      if (competitorDomains.has(key)) {
        const cur = competitorTallies.get(key);
        if (cur) cur.count += 1;
      }
    }
  }
  const topCompetitors = Array.from(competitorTallies.values())
    .filter((c) => c.count > 0)
    .sort((a, b) => b.count - a.count)
    .slice(0, 2);

  let compPart = "";
  if (topCompetitors.length === 2) {
    compPart = ` Competitors ${topCompetitors[0].name} and ${topCompetitors[1].name} are cited in ${topCompetitors[0].count} and ${topCompetitors[1].count} queries respectively.`;
  } else if (topCompetitors.length === 1) {
    compPart = ` Competitor ${topCompetitors[0].name} is cited in ${topCompetitors[0].count} queries.`;
  }

  return `${brand} is visible in Perplexity: mentioned in ${mentioned} of ${total} queries, cited as a source in ${cited} of ${total}.${compPart}`;
}

export default function ScoreHero({ report }: Props) {
  const score = report.aeo_score ?? 0;
  const level = getLevel(score);
  const delta = deltaToNextLevel(score);
  const summary = buildSummary(report);

  return (
    <section className={`rounded-2xl border border-neutral-200 ${level.bgClass} px-6 py-10 sm:px-10 sm:py-14`}>
      <div className="flex flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm uppercase tracking-wide text-neutral-500">AEO Score</p>
          <div className="mt-2 flex items-baseline gap-3">
            <span className={`text-7xl font-semibold tracking-tight ${level.textClass} sm:text-8xl`}>
              {score.toFixed(0)}
            </span>
            <span className="text-2xl text-neutral-400">/ 100</span>
          </div>
        </div>
        <div className="text-left sm:text-right">
          <span className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${level.textClass} ${level.bgClass} ring-1 ring-inset ring-current/20`}>
            {level.label}
          </span>
          {delta && (
            <p className="mt-3 text-sm text-neutral-600">
              To &ldquo;{delta.label}&rdquo; — <span className="font-medium">{delta.points} {delta.points === 1 ? "point" : "points"}</span>
            </p>
          )}
        </div>
      </div>
      <p className="mt-8 max-w-3xl text-base leading-relaxed text-neutral-700">{summary}</p>
    </section>
  );
}
