import UrlForm from "@/components/UrlForm";

const workflow = [
  {
    step: "01",
    title: "Read the site",
    text: "We fetch the homepage and key sections to understand the brand, market, products, and competitors.",
  },
  {
    step: "02",
    title: "Generate demand",
    text: "We generate 10 commercial AI queries that a buyer realistically asks before making a decision.",
  },
  {
    step: "03",
    title: "Check the results",
    text: "We run the queries through Perplexity Sonar Pro and capture mentions, citations, sources, and sentiment.",
  },
];

const reportSignals = [
  "AEO Score 0-100",
  "Citation Rate",
  "Mention Rate",
  "Source Share of Voice",
  "Breakdown by 10 prompts",
  "Actionable insights",
];

const sourceRows = [
  { domain: "brand.com", value: 38, tone: "Brand" },
  { domain: "reviewhub.com", value: 24, tone: "Source" },
  { domain: "competitor.com", value: 18, tone: "Competitor" },
  { domain: "media.com", value: 12, tone: "Media" },
];

const navLinks = ["Methodology", "Report", "Sources", "FAQ"];

const readinessItems = [
  "Brand found in answers",
  "Sources cited consistently",
  "Competitive gaps identified",
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-cream font-display text-ink antialiased">
      {/* Nav */}
      <header className="sticky top-0 z-30 border-b border-ink/12 bg-cream/90 backdrop-blur">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3 sm:px-8 lg:px-10">
          <div className="flex items-center gap-3">
            <span className="flex h-6 w-6 items-center justify-center bg-orange text-xs font-bold text-cream">
              A
            </span>
            <span className="text-sm font-bold tracking-tight">AEO Grader</span>
          </div>
          <div className="hidden items-center gap-7 md:flex">
            {navLinks.map((link) => (
              <span
                key={link}
                className="text-sm text-ink/70 transition-colors hover:text-ink"
              >
                {link}
              </span>
            ))}
          </div>
          <a
            href="#run"
            className="bg-ink px-5 py-2.5 text-sm font-medium text-cream transition-colors hover:bg-orange"
          >
            Run audit
          </a>
        </nav>
      </header>

      {/* Hero */}
      <section className="border-b border-ink/12">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:px-10 lg:py-20">
          <div className="space-y-8">
            <span className="inline-flex border border-ink/15 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink/65">
              Perplexity visibility report — no subscription
            </span>
            <h1 className="text-5xl font-bold leading-[0.95] tracking-tight sm:text-6xl lg:text-7xl">
              See how AI search perceives your brand
            </h1>
            <p className="max-w-xl text-lg leading-8 text-ink/70">
              AEO Grader runs your site through Perplexity search scenarios and
              returns a report: where your brand is cited, where it loses to
              competitors, and which sources shape the results.
            </p>
            <div id="run" className="border border-ink/15 bg-cream p-4 sm:p-5">
              <UrlForm />
            </div>
            <div className="grid max-w-lg grid-cols-3 border border-ink/15">
              {[
                ["10", "AI queries"],
                ["60-90s", "to report"],
                ["0-100", "AEO Score"],
              ].map(([value, label], i) => (
                <div
                  key={label}
                  className={`px-4 py-4 ${i > 0 ? "border-l border-ink/15" : ""}`}
                >
                  <div className="text-2xl font-bold">{value}</div>
                  <div className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink/55">
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <PixelHero />
        </div>
      </section>

      {/* Methodology */}
      <section className="border-b border-ink/12">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-10 lg:py-24">
          <div className="mb-12 max-w-2xl space-y-4">
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
              Methodology
            </span>
            <h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              The audit mirrors a real buyer&apos;s journey
            </h2>
          </div>
          <div className="grid border border-ink/12 md:grid-cols-3">
            {workflow.map((item, i) => (
              <article
                key={item.step}
                className={`p-7 ${i > 0 ? "border-t border-ink/12 md:border-l md:border-t-0" : ""}`}
              >
                <div className="mb-8 flex items-center justify-between">
                  <span className="flex h-8 w-8 items-center justify-center bg-orange/10 font-mono text-sm text-orange">
                    {item.step}
                  </span>
                  <PixelGlyph index={i} />
                </div>
                <h3 className="mb-3 text-xl font-bold">{item.title}</h3>
                <p className="leading-7 text-ink/65">{item.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* What's in the report — dark band */}
      <section className="border-b border-ink/12 bg-navy text-cream">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-10 lg:py-24">
          <div className="mx-auto mb-12 max-w-3xl space-y-5 text-center">
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange-bright">
              What&apos;s in the report
            </span>
            <h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Not just a score — a map of influence sources
            </h2>
            <p className="mx-auto max-w-xl text-lg leading-8 text-cream/70">
              The report shows why the AI answer formed the way it did: which
              domains are cited, where your brand appears, and where competitors
              capture visibility.
            </p>
          </div>
          <div className="grid border border-cream/15 sm:grid-cols-2 lg:grid-cols-3">
            {reportSignals.map((signal, i) => (
              <div
                key={signal}
                className={`flex items-center gap-3 p-6 text-lg font-medium ${
                  i % 3 !== 0 ? "lg:border-l lg:border-cream/15" : ""
                } ${i >= 1 ? "border-t border-cream/15" : ""} ${
                  i % 2 !== 0 ? "sm:border-l sm:border-cream/15" : ""
                } ${i >= 2 ? "sm:border-t" : "sm:border-t-0"} lg:border-t`}
              >
                <span className="h-2 w-2 shrink-0 bg-orange" />
                {signal}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Who it's for + readiness */}
      <section className="border-b border-ink/12">
        <div className="mx-auto grid max-w-7xl gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-10 lg:py-24">
          <div className="space-y-5">
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
              Who it&apos;s for
            </span>
            <h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              For teams that need a fast signal before SEO, PR, and content work
            </h2>
            <p className="max-w-2xl text-lg leading-8 text-ink/65">
              Use the one-shot audit as an entry-level diagnostic: spot gaps,
              benchmark against competitors, and identify which pages or
              publications to strengthen first.
            </p>
          </div>
          <div className="border border-ink/15 bg-cream">
            <div className="flex items-center justify-between border-b border-ink/12 px-6 py-4">
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink/55">
                Readiness
              </span>
              <span className="bg-orange px-3 py-1 text-sm font-semibold text-cream">
                Agent Friendly
              </span>
            </div>
            <div className="space-y-5 p-6">
              {readinessItems.map((item) => (
                <div key={item} className="flex items-center gap-4">
                  <span className="h-3 w-3 bg-orange" />
                  <span className="text-lg">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Final CTA */}
      <section className="px-5 py-16 sm:px-8 lg:px-10 lg:py-24">
        <div className="mx-auto max-w-7xl border border-ink/15 bg-cream p-7 sm:p-12">
          <div className="grid gap-10 lg:grid-cols-[1fr_0.9fr] lg:items-center">
            <div className="space-y-4">
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
                Run an audit
              </span>
              <h2 className="text-3xl font-bold leading-tight tracking-tight sm:text-5xl">
                Enter your domain and get your first AI visibility snapshot
              </h2>
            </div>
            <UrlForm />
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-ink/12">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-3 px-5 py-8 sm:flex-row sm:items-center sm:px-8 lg:px-10">
          <span className="text-sm font-bold tracking-tight">AEO Grader</span>
          <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink/45">
            Single-shot AI visibility audit
          </span>
        </div>
      </footer>
    </main>
  );
}

/* --- Orange pixel-grid hero graphic with a floating prompt card --- */

const PIXEL_PALETTE: Record<string, string> = {
  b: "bg-orange-bright",
  o: "bg-orange",
  r: "bg-orange-red",
  d: "bg-orange-deep",
  ".": "bg-transparent",
};

// 9 columns wide
const PIXEL_PATTERN = [
  ".", "o", "b", "o", "r", "o", "d", "o", ".",
  "o", "r", "o", "d", "b", "o", "r", "o", "b",
  "b", "o", "r", "o", "o", "d", "o", "b", "o",
  "o", "d", "o", "b", "o", "r", "o", "o", "r",
  "r", "o", "b", "o", "d", "o", "b", "o", "o",
  "o", "b", "o", "r", "o", "o", "d", "o", "b",
  ".", "o", "d", "o", "b", "o", "r", "o", ".",
];

function PixelHero() {
  return (
    <div className="relative aspect-square w-full overflow-hidden border border-ink/12 bg-orange">
      {/* colored cells */}
      <div className="grid h-full w-full grid-cols-9">
        {PIXEL_PATTERN.map((key, i) => (
          <div key={i} className={PIXEL_PALETTE[key] ?? "bg-orange"} />
        ))}
      </div>

      {/* faint grid lines */}
      <div className="pixel-grid-lines pointer-events-none absolute inset-0" />

      {/* floating diamonds */}
      <span className="animate-diamond absolute right-[14%] top-[16%] h-9 w-9 bg-orange-deep" />
      <span className="absolute bottom-[20%] left-[16%] h-7 w-7 rotate-45 bg-orange-red" />

      {/* mono corner labels */}
      <span className="absolute bottom-3 left-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/70">
        AEO Grader
      </span>
      <span className="absolute right-3 top-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/70">
        AI Visibility
      </span>

      {/* floating prompt card */}
      <div className="absolute left-1/2 top-1/2 w-[80%] max-w-sm -translate-x-1/2 -translate-y-1/2 border border-ink/15 bg-cream p-4 shadow-[0_24px_60px_rgba(13,13,13,0.25)]">
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink/45">
          Prompt sample
        </p>
        <p className="mt-2 leading-7 text-ink">
          Which services should I choose for automating e-commerce support?
        </p>
        <div className="mt-4 space-y-2">
          {sourceRows.slice(0, 3).map((row) => (
            <div key={row.domain} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-ink/70">{row.domain}</span>
                <span className="text-ink/40">{row.tone}</span>
              </div>
              <div className="h-1.5 bg-ink/10">
                <div className="h-full bg-orange" style={{ width: `${row.value}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* Tiny pixel-art glyphs for the methodology tiles */
function PixelGlyph({ index }: { index: number }) {
  const shades = ["bg-orange", "bg-orange-red", "bg-orange-deep"];
  const cells = [
    [1, 1, 0, 1],
    [0, 1, 1, 0],
    [1, 0, 1, 1],
  ][index % 3];
  const shade = shades[index % 3];
  return (
    <div className="grid grid-cols-2 gap-0.5">
      {cells.map((on, i) => (
        <span key={i} className={`h-2 w-2 ${on ? shade : "bg-ink/10"}`} />
      ))}
    </div>
  );
}
