import type { ReportOut } from "@/lib/types";
import { SENTIMENT_LABEL } from "@/lib/score";

interface Props {
  report: ReportOut;
}

export default function ActionableInsights({ report }: Props) {
  const priorityPrompts = report.prompt_results
    .filter((p) => !p.brand_cited && !p.brand_mentioned && (p.competitors_cited.length > 0 || p.competitors_mentioned.length > 0))
    .slice(0, 5);

  const sov = report.source_share_of_voice ?? [];
  const otherSources = sov.filter((e) => !e.is_brand && !e.is_competitor).slice(0, 10);

  const negativeFlags = report.prompt_results.filter((p) => p.sentiment === "negative");

  return (
    <section className="space-y-8">
      <h2 className="text-xl font-semibold">What to do</h2>

      <SubSection title="Priority queries to address" hint="Queries where competitors appear but you don't">
        {priorityPrompts.length === 0 ? (
          <p className="text-sm text-neutral-500">No queries with clear losses to competitors found.</p>
        ) : (
          <ul className="space-y-3">
            {priorityPrompts.map((p) => (
              <li key={p.id} className="rounded-lg border border-neutral-200 bg-white p-4">
                <p className="font-medium text-neutral-900">{p.prompt}</p>
                {p.competitors_cited.length > 0 && (
                  <p className="mt-1 text-sm text-neutral-600">
                    Competitors in sources: {p.competitors_cited.join(", ")}
                  </p>
                )}
                {p.competitors_mentioned.length > 0 && (
                  <p className="mt-1 text-sm text-neutral-600">
                    Mentioned in text: {p.competitors_mentioned.join(", ")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        )}
      </SubSection>

      <SubSection title="Top sources for placement" hint="Third-party domains that Perplexity cites in your niche">
        {otherSources.length === 0 ? (
          <p className="text-sm text-neutral-500">No third-party sources found.</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {otherSources.map((d) => (
              <li key={d.domain}>
                <a
                  href={`https://${d.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-neutral-200 bg-white px-3 py-2 text-sm text-neutral-700 hover:border-neutral-400"
                >
                  <span className="font-medium">{d.domain}</span>
                  <span className="text-xs text-neutral-400">{d.count} citations</span>
                </a>
              </li>
            ))}
          </ul>
        )}
      </SubSection>

      {negativeFlags.length > 0 && (
        <SubSection title="Sentiment flags" hint="Queries where AI responded negatively about the brand">
          <ul className="space-y-3">
            {negativeFlags.map((p) => (
              <li key={p.id} className="rounded-lg border border-red-200 bg-red-50 p-4">
                <p className="font-medium text-neutral-900">{p.prompt}</p>
                <p className="mt-1 text-xs text-red-700">
                  Sentiment: {SENTIMENT_LABEL[p.sentiment ?? "negative"]}
                </p>
                <p className="mt-2 line-clamp-3 text-sm text-neutral-700">{p.raw_response.slice(0, 400)}…</p>
              </li>
            ))}
          </ul>
        </SubSection>
      )}
    </section>
  );
}

function SubSection({ title, hint, children }: { title: string; hint: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-base font-medium text-neutral-900">{title}</h3>
      <p className="mb-3 text-sm text-neutral-500">{hint}</p>
      {children}
    </div>
  );
}
