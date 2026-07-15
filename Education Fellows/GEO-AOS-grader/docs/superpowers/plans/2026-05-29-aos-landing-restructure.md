# AOS Landing Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the homepage (`/`) with a full AOS (Agent Operability Score) landing page in the existing Mistral visual language, hiding the AEO Grader landing but preserving its code.

**Architecture:** `page.tsx` is fully rewritten as the AOS landing — 7 sections (nav, hero, shift, scoring blocks, signals, readiness, CTA). `AgentReportForm` is restyled to match the Mistral design system (squared corners, orange accent, ink button). The AEO landing is preserved in `page.old.tsx` (already exists as a backup of the pre-Mistral design — we overwrite it with the current Mistral AEO content so neither version is lost). All AOS scan routing (`/agent-report/[domain]`) is unchanged.

**Tech Stack:** Next.js 14 App Router, Tailwind CSS, TypeScript, Space Grotesk + Space Mono fonts, existing Mistral design tokens (cream/ink/navy/orange).

---

## File Map

| File | Action | What changes |
|---|---|---|
| `frontend/app/page.old.tsx` | Overwrite | Replace pre-Mistral AEO backup with current Mistral AEO landing (so the polished version is preserved) |
| `frontend/app/layout.tsx` | Modify | Update `metadata` title + description for AOS |
| `frontend/app/agent-report/AgentReportForm.tsx` | Modify | Remove `rounded-lg`, adopt Mistral design tokens (squared input, ink/orange button) |
| `frontend/app/page.tsx` | Full rewrite | AOS landing — 7 sections, imports `AgentReportForm` |

**Unchanged:** `frontend/app/agent-report/page.tsx`, `frontend/app/agent-report/[domain]/page.tsx`, `frontend/app/report/[id]/page.tsx`, `frontend/app/analyze/[id]/page.tsx`, `frontend/components/UrlForm.tsx`, all `lib/` files.

---

## Task 1: Preserve AEO landing and update site metadata

**Files:**
- Overwrite: `frontend/app/page.old.tsx`
- Modify: `frontend/app/layout.tsx`

- [ ] **Step 1: Copy current Mistral AEO landing to page.old.tsx**

Read `frontend/app/page.tsx` and write its entire contents verbatim to `frontend/app/page.old.tsx`, replacing what's there. This preserves the polished Mistral AEO design in case it's needed later.

> The file already exists (it holds a pre-Mistral backup). Overwrite it.

- [ ] **Step 2: Update metadata in layout.tsx**

In `frontend/app/layout.tsx`, replace the `metadata` object:

```tsx
export const metadata: Metadata = {
  title: "AOS Grader",
  description: "See how AI agents experience your platform — machine interfaces, discovery signals, auth, and more.",
};
```

- [ ] **Step 3: Start the dev server and verify the site still loads**

```bash
cd frontend && npm run dev
```

Open http://localhost:3000. The current AEO landing should still show (we haven't touched `page.tsx` yet). The browser tab title should now read "AOS Grader". Confirm, then keep the dev server running.

- [ ] **Step 4: Commit**

```bash
git add frontend/app/page.old.tsx frontend/app/layout.tsx
git commit -m "chore: preserve AEO landing in page.old.tsx and update site metadata to AOS"
```

---

## Task 2: Restyle AgentReportForm for Mistral design language

**Files:**
- Modify: `frontend/app/agent-report/AgentReportForm.tsx`

The current form uses `rounded-lg` (conflicts with Mistral's zero-radius rule) and neutral Tailwind colors. Replace with squared corners and the design system tokens (`ink`, `orange`, `cream`).

- [ ] **Step 1: Rewrite AgentReportForm.tsx**

Replace the entire file with:

```tsx
"use client"
import { useRouter } from "next/navigation"
import { useState } from "react"
import { normalizeUrl } from "@/lib/agent-check/url-utils"

export default function AgentReportForm() {
  const router = useRouter()
  const [url, setUrl] = useState("")
  const [error, setError] = useState<string | null>(null)

  function onSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    try {
      const { domain } = normalizeUrl(url.trim())
      router.push(`/agent-report/${encodeURIComponent(domain)}`)
    } catch {
      setError("Enter a valid URL — e.g. stripe.com")
    }
  }

  return (
    <form onSubmit={onSubmit} className="w-full space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          type="text"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="stripe.com or https://stripe.com"
          className="flex-1 border border-ink/20 bg-transparent px-4 py-3 text-base text-ink placeholder:text-ink/40 outline-none focus:border-ink transition-colors"
          required
        />
        <button
          type="submit"
          disabled={!url.trim()}
          className="bg-ink px-6 py-3 text-sm font-medium text-cream transition-colors hover:bg-orange disabled:cursor-not-allowed disabled:opacity-50"
        >
          Run scan
        </button>
      </div>
      {error && <p className="text-sm text-red-600">{error}</p>}
      <p className="font-mono text-[11px] uppercase tracking-[0.1em] text-ink/45">
        Scan takes ~30 seconds.
      </p>
    </form>
  )
}
```

- [ ] **Step 2: Check the form still works on /agent-report**

Navigate to http://localhost:3000/agent-report. The form should render with squared corners, ink button that turns orange on hover. Submit a domain (e.g. `stripe.com`) — verify it routes to `/agent-report/stripe.com`.

- [ ] **Step 3: Commit**

```bash
git add frontend/app/agent-report/AgentReportForm.tsx
git commit -m "style: restyle AgentReportForm to match Mistral design language"
```

---

## Task 3: Rewrite page.tsx as the AOS landing

**Files:**
- Full rewrite: `frontend/app/page.tsx`

This is the core task. Replace the entire file with the AOS landing. The page is a server component (no `"use client"`) — the interactive form is handled by the imported `AgentReportForm` client component. `PixelHero` and `PixelGlyph` stay as inline components at the bottom of the file.

- [ ] **Step 1: Write the new page.tsx**

Replace the entire `frontend/app/page.tsx` with:

```tsx
import AgentReportForm from "./agent-report/AgentReportForm"

// ─── Data ────────────────────────────────────────────────────────────────────

const scoringBlocks = [
  {
    name: "Machine Interface",
    pts: 30,
    desc: "MCP servers, OpenAPI specs, and structured API surfaces that agents can discover and call.",
  },
  {
    name: "Browser Operability",
    pts: 25,
    desc: "Whether an AI browser agent can navigate, interact, and complete tasks on your site.",
  },
  {
    name: "Agent Discovery",
    pts: 25,
    desc: "llms.txt, robots.txt agent permissions, and Schema.org markup that orient AI agents.",
  },
  {
    name: "Auth & Security",
    pts: 20,
    desc: "OAuth flows, CORS policy, and security posture for programmatic agent access.",
  },
]

const detectionSignals = [
  "MCP servers",
  "OpenAPI specs",
  "OAuth support",
  "CORS policy",
  "llms.txt",
  "robots.txt permissions",
  "Schema.org markup",
  "SDK documentation",
]

const agentReadinessItems = [
  "MCP endpoint reachable",
  "OpenAPI spec found",
  "OAuth flow supported",
]

const navLinks = ["The Shift", "Scoring", "Signals", "FAQ"]

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HomePage() {
  return (
    <main className="min-h-screen bg-cream font-display text-ink antialiased">

      {/* ── Nav ── */}
      <header className="sticky top-0 z-30 border-b border-ink/12 bg-cream/90 backdrop-blur">
        <nav className="mx-auto flex max-w-7xl items-center justify-between px-5 py-3 sm:px-8 lg:px-10">
          <div className="flex items-center gap-3">
            <span className="flex h-6 w-6 items-center justify-center bg-orange text-xs font-bold text-cream">
              A
            </span>
            <span className="text-sm font-bold tracking-tight">AOS Grader</span>
          </div>
          <div className="hidden items-center gap-7 md:flex">
            {navLinks.map((link) => (
              <span
                key={link}
                className="cursor-pointer text-sm text-ink/70 transition-colors hover:text-ink"
              >
                {link}
              </span>
            ))}
          </div>
          <a
            href="#run"
            className="bg-ink px-5 py-2.5 text-sm font-medium text-cream transition-colors hover:bg-orange"
          >
            Run scan
          </a>
        </nav>
      </header>

      {/* ── Hero ── */}
      <section className="border-b border-ink/12">
        <div className="mx-auto grid max-w-7xl gap-10 px-5 py-14 sm:px-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:px-10 lg:py-20">
          <div className="space-y-8">
            <span className="inline-flex border border-ink/15 px-3 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-ink/65">
              Agent operability scan — no signup
            </span>
            <h1 className="text-5xl font-bold leading-[0.95] tracking-tight sm:text-6xl lg:text-7xl">
              See how agents feel when interacting with your platform.
            </h1>
            <p className="max-w-xl text-lg leading-8 text-ink/70">
              AOS Grader probes your platform for machine-readable interfaces,
              agent discovery signals, and authentication flows — then scores
              how ready it is for AI agents to operate.
            </p>
            <div id="run" className="border border-ink/15 bg-cream p-4 sm:p-5">
              <AgentReportForm />
            </div>
            <div className="grid max-w-lg grid-cols-3 border border-ink/15">
              {[
                ["0–100", "AOS Score"],
                ["4", "blocks checked"],
                ["~30s", "to report"],
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

      {/* ── The Shift ── */}
      <section className="border-b border-ink/12">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-10 lg:py-24">
          <div className="mb-12 max-w-2xl space-y-4">
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
              Why operability
            </span>
            <h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Being found isn&apos;t enough. Agents need to act.
            </h2>
          </div>
          <div className="grid border border-ink/12 md:grid-cols-2">
            <div className="space-y-4 p-8">
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink/45">
                AEO / SEO
              </span>
              <h3 className="text-2xl font-bold">Can AI find you?</h3>
              <p className="leading-7 text-ink/65">
                Search optimization ensures your brand appears in AI-generated
                answers and citations. Necessary, but no longer sufficient.
              </p>
            </div>
            <div className="space-y-4 border-t border-ink/12 bg-orange/5 p-8 md:border-l md:border-t-0">
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
                AOS
              </span>
              <h3 className="text-2xl font-bold">Can AI use you?</h3>
              <p className="leading-7 text-ink/65">
                Agent operability determines whether an AI agent can
                authenticate, discover your APIs, and complete tasks — not just
                reference your name.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── 4 Scoring Blocks ── */}
      <section className="border-b border-ink/12">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-10 lg:py-24">
          <div className="mb-12 max-w-2xl space-y-4">
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
              Scoring
            </span>
            <h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Four dimensions of agent readiness
            </h2>
          </div>
          <div className="grid border border-ink/12 md:grid-cols-2">
            {scoringBlocks.map((block, i) => (
              <article
                key={block.name}
                className={`p-7 ${i % 2 !== 0 ? "md:border-l md:border-ink/12" : ""} ${i >= 2 ? "border-t border-ink/12" : ""}`}
              >
                <div className="mb-6 flex items-start justify-between">
                  <PixelGlyph index={i} />
                  <span className="border border-orange/30 px-2 py-1 font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
                    {block.pts} pts
                  </span>
                </div>
                <h3 className="mb-3 text-xl font-bold">{block.name}</h3>
                <p className="leading-7 text-ink/65">{block.desc}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      {/* ── What we detect — dark navy band ── */}
      <section className="border-b border-ink/12 bg-navy text-cream">
        <div className="mx-auto max-w-7xl px-5 py-16 sm:px-8 lg:px-10 lg:py-24">
          <div className="mx-auto mb-12 max-w-3xl space-y-5 text-center">
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange-bright">
              What we detect
            </span>
            <h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              Concrete signals, not guesswork
            </h2>
            <p className="mx-auto max-w-xl text-lg leading-8 text-cream/70">
              Every check targets a real signal an agent would encounter —
              machine-readable interfaces, discovery files, and authentication
              endpoints.
            </p>
          </div>
          <div className="grid border border-cream/15 sm:grid-cols-2 lg:grid-cols-4">
            {detectionSignals.map((signal, i) => (
              <div
                key={signal}
                className={[
                  "flex items-center gap-3 p-6 text-base font-medium",
                  i > 0 ? "border-t border-cream/15" : "",
                  i % 2 !== 0 ? "sm:border-l sm:border-cream/15 sm:border-t-0" : "",
                  i % 2 === 0 && i >= 2 ? "sm:border-t border-cream/15" : "",
                  i % 4 !== 0 ? "lg:border-l lg:border-cream/15 lg:border-t-0" : "",
                  i % 4 === 0 && i >= 4 ? "lg:border-t border-cream/15" : "",
                ]
                  .filter(Boolean)
                  .join(" ")}
              >
                <span className="h-2 w-2 shrink-0 bg-orange" />
                {signal}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Who it's for + readiness card ── */}
      <section className="border-b border-ink/12">
        <div className="mx-auto grid max-w-7xl gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center lg:px-10 lg:py-24">
          <div className="space-y-5">
            <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
              Who it&apos;s for
            </span>
            <h2 className="text-4xl font-bold leading-tight tracking-tight sm:text-5xl">
              For platforms that want to be agent-ready
            </h2>
            <p className="max-w-2xl text-lg leading-8 text-ink/65">
              API-first SaaS, developer tools, and marketplaces that expect AI
              agents to become a primary user class. Use AOS as an instant
              diagnostic before you invest in agent integrations.
            </p>
          </div>
          <div className="border border-ink/15 bg-cream">
            <div className="flex items-center justify-between border-b border-ink/12 px-6 py-4">
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink/55">
                Sample verdict
              </span>
              <span className="bg-orange px-3 py-1 text-sm font-semibold text-cream">
                Agent Ready
              </span>
            </div>
            <div className="space-y-5 p-6">
              {agentReadinessItems.map((item) => (
                <div key={item} className="flex items-center gap-4">
                  <span className="h-3 w-3 bg-orange" />
                  <span className="text-lg">{item}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ── Final CTA ── */}
      <section className="px-5 py-16 sm:px-8 lg:px-10 lg:py-24">
        <div className="mx-auto max-w-7xl border border-ink/15 bg-cream p-7 sm:p-12">
          <div className="grid gap-10 lg:grid-cols-[1fr_0.9fr] lg:items-center">
            <div className="space-y-4">
              <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-orange">
                Run a scan
              </span>
              <h2 className="text-3xl font-bold leading-tight tracking-tight sm:text-5xl">
                Find out if your platform is ready for the agent era
              </h2>
            </div>
            <AgentReportForm />
          </div>
        </div>
      </section>

      {/* ── Footer ── */}
      <footer className="border-t border-ink/12">
        <div className="mx-auto flex max-w-7xl flex-col items-start justify-between gap-3 px-5 py-8 sm:flex-row sm:items-center sm:px-8 lg:px-10">
          <span className="text-sm font-bold tracking-tight">AOS Grader</span>
          <span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink/45">
            Agent operability scan
          </span>
        </div>
      </footer>
    </main>
  )
}

// ─── PixelHero ────────────────────────────────────────────────────────────────

const PIXEL_PALETTE: Record<string, string> = {
  b: "bg-orange-bright",
  o: "bg-orange",
  r: "bg-orange-red",
  d: "bg-orange-deep",
  ".": "bg-transparent",
}

const PIXEL_PATTERN = [
  ".", "o", "b", "o", "r", "o", "d", "o", ".",
  "o", "r", "o", "d", "b", "o", "r", "o", "b",
  "b", "o", "r", "o", "o", "d", "o", "b", "o",
  "o", "d", "o", "b", "o", "r", "o", "o", "r",
  "r", "o", "b", "o", "d", "o", "b", "o", "o",
  "o", "b", "o", "r", "o", "o", "d", "o", "b",
  ".", "o", "d", "o", "b", "o", "r", "o", ".",
]

const probeRows = [
  { label: "MCP endpoint", status: "Found", ok: true },
  { label: "OpenAPI spec", status: "Found", ok: true },
  { label: "OAuth support", status: "Missing", ok: false },
]

function PixelHero() {
  return (
    <div className="relative aspect-square w-full overflow-hidden border border-ink/12 bg-orange">
      <div className="grid h-full w-full grid-cols-9">
        {PIXEL_PATTERN.map((key, i) => (
          <div key={i} className={PIXEL_PALETTE[key] ?? "bg-orange"} />
        ))}
      </div>
      <div className="pixel-grid-lines pointer-events-none absolute inset-0" />
      <span className="animate-diamond absolute right-[14%] top-[16%] h-9 w-9 bg-orange-deep" />
      <span className="absolute bottom-[20%] left-[16%] h-7 w-7 rotate-45 bg-orange-red" />
      <span className="absolute bottom-3 left-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/70">
        AOS Grader
      </span>
      <span className="absolute right-3 top-3 font-mono text-[10px] uppercase tracking-[0.18em] text-ink/70">
        Operability
      </span>
      <div className="absolute left-1/2 top-1/2 w-[80%] max-w-sm -translate-x-1/2 -translate-y-1/2 border border-ink/15 bg-cream p-4 shadow-[0_24px_60px_rgba(13,13,13,0.25)]">
        <p className="font-mono text-[10px] uppercase tracking-[0.14em] text-ink/45">
          Capability probe
        </p>
        <p className="mt-2 leading-7 text-ink">stripe.com</p>
        <div className="mt-4 space-y-3">
          {probeRows.map((row) => (
            <div key={row.label} className="flex items-center justify-between text-xs">
              <span className="text-ink/70">{row.label}</span>
              <span className={row.ok ? "font-medium text-orange" : "text-ink/40"}>
                {row.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// ─── PixelGlyph ───────────────────────────────────────────────────────────────

function PixelGlyph({ index }: { index: number }) {
  const shades = ["bg-orange", "bg-orange-red", "bg-orange-deep", "bg-orange-bright"]
  const cells = [
    [1, 1, 0, 1],
    [0, 1, 1, 0],
    [1, 0, 1, 1],
    [1, 1, 1, 0],
  ][index % 4]
  const shade = shades[index % 4]
  return (
    <div className="grid grid-cols-2 gap-0.5">
      {cells.map((on, i) => (
        <span key={i} className={`h-2 w-2 ${on ? shade : "bg-ink/10"}`} />
      ))}
    </div>
  )
}
```

- [ ] **Step 2: Run type check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors. If you see an error about `AgentReportForm` import path, verify the relative path is `"./agent-report/AgentReportForm"` from `app/page.tsx`.

- [ ] **Step 3: Visual check — full landing walk-through**

With dev server running at http://localhost:3000, verify each section:
1. **Nav** — "AOS Grader" wordmark, orange A glyph, "Run scan" button scrolls to hero form
2. **Hero** — correct headline, URL form works (submit `stripe.com` → navigates to `/agent-report/stripe.com`), 3-stat strip shows 0–100 / 4 / ~30s, PixelHero shows capability probe card with Found/Missing statuses
3. **The Shift** — two columns, orange "AOS" eyebrow on right column, right side has `bg-orange/5` tint
4. **Scoring Blocks** — 2×2 grid, each block has a pixel glyph, orange "N pts" badge, name, description
5. **What we detect** — dark navy band, 8 signals in a 4-col grid on desktop
6. **Who it's for** — "Agent Ready" orange badge on readiness card, 3 checklist items
7. **Final CTA** — "Find out if your platform is ready for the agent era", form works
8. **Footer** — "AOS Grader" / "Agent operability scan"

- [ ] **Step 4: Check /agent-report still loads**

Navigate to http://localhost:3000/agent-report. The plain AgentReportForm page should render and still be functional.

- [ ] **Step 5: Commit**

```bash
git add frontend/app/page.tsx
git commit -m "feat: rewrite homepage as AOS landing (7-section Option B)"
```

---

## Task 4: Final cleanup commit

- [ ] **Step 1: Run full type check one more time**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 2: Confirm AEO routes still work (smoke test)**

Navigate to http://localhost:3000/report/any-id — it should show the AEO report page (or a not-found state), not crash. Navigate to http://localhost:3000/analyze/any-id — same. These routes are untouched.

- [ ] **Step 3: Commit plan completion note**

```bash
git add .
git commit -m "chore: AOS landing restructure complete — AEO grader hidden, AOS at root"
```

---

## Self-Review

**Spec coverage:**
- [x] `/` becomes AOS landing → Task 3
- [x] AEO landing preserved (not deleted) → Task 1 (page.old.tsx overwrite)
- [x] Mistral visual language reused → Task 3 (all same component patterns)
- [x] Hero headline fixed: "See how agents feel when interacting with your platform." → Task 3
- [x] All 4 scoring blocks as live → Task 3 (no beta/coming-soon tag)
- [x] Readiness card kept → Task 3 (Section 6)
- [x] Form routes to `/agent-report/[domain]` → Task 2 (AgentReportForm unchanged in logic)
- [x] "The Shift" band (new section) → Task 3
- [x] Dark navy signals band → Task 3
- [x] AEO results routes left intact → addressed in scope note (no tasks modify them)
- [x] Metadata updated → Task 1

**Placeholder scan:** No TBDs or TODOs. All code is complete.

**Type consistency:** `AgentReportForm` default export used identically in Task 2 (definition) and Task 3 (import at `"./agent-report/AgentReportForm"`). `PixelHero` and `PixelGlyph` defined and used in same file. `probeRows`, `scoringBlocks`, `detectionSignals`, `agentReadinessItems` defined at top of page.tsx and consumed inline — no cross-task type drift.
