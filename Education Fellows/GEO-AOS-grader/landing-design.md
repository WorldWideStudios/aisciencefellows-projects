# Landing Page — Mistral-Style Design Language

Visual language for the homepage (`frontend/app/page.tsx`), modeled closely on
[mistral.ai](https://mistral.ai/). All existing AEO Grader **copy is preserved** —
only the visual layer changes. The previous design is kept at
`frontend/app/page.old.tsx`.

> Scope: homepage only. The root `design.md` still governs the app/report
> components (ScoreHero, BlockCard, grade colors, etc.) and is unchanged.

---

## Core principles

1. **Sharp corners.** No `border-radius` anywhere. Squared edges are the single
   strongest Mistral signature.
2. **Hairline grid.** Thin `1px` low-opacity borders divide every section and
   tile, producing an architectural grid feel. Sections butt up against each
   other with shared border lines.
3. **Warm cream canvas.** Off-white paper background, near-black ink.
4. **Bold grotesque display.** Large, tight-leading headlines.
5. **Monospace micro-labels.** Small uppercase, letter-spaced mono text for
   eyebrows and corner registration labels.
6. **Pixel / checkerboard motif.** An orange grid of colored squares with a few
   rotated "diamond" squares — the playful retro graphic Mistral uses in hero
   and feature blocks.
7. **One dark section.** A near-black navy block for contrast (Mistral's
   "deployments" / privacy band).

---

## Tokens

### Color

| Token | Hex | Use |
|---|---|---|
| `--cream` | `#FAF9F5` | page background |
| `--ink` | `#0D0D0D` | primary text, dark UI, buttons |
| `--navy` | `#10101C` | dark section background |
| `--orange` | `#FA520F` | primary accent, buttons, bars |
| `--orange-bright` | `#FF8205` | pixel-grid light cell |
| `--orange-red` | `#E2330C` | pixel-grid mid cell |
| `--orange-deep` | `#B0190A` | pixel-grid dark cell |
| hairline | `rgba(13,13,13,0.12)` | borders, grid lines |
| hairline-light | `rgba(255,255,255,0.16)` | borders inside dark section |

### Type

- **Display / headings:** `Space Grotesk` (700), tight leading
  (`leading-[0.95]`), loaded via `next/font`.
- **Body:** Space Grotesk (400/500) — single family, like Mistral.
- **Micro-labels / code:** `Space Mono`, `uppercase`, `tracking-[0.12em]`,
  `text-[11px]`.

### Geometry

- Radius: `0` everywhere.
- Section horizontal padding: `px-5 sm:px-8 lg:px-10`, content `max-w-7xl`.
- Standard hairline: `border border-[rgba(13,13,13,0.12)]`.

---

## Reusable patterns

```tsx
// Micro-label (eyebrow / corner registration)
<span className="font-mono text-[11px] uppercase tracking-[0.12em] text-ink/55">
  Methodology
</span>

// Squared primary button
<button className="bg-ink px-5 py-2.5 text-sm font-medium text-cream hover:bg-orange transition-colors">
  Run audit
</button>

// Pill tag (mono, bordered)
<span className="border border-ink/15 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.1em] text-ink/60">
  Citation Rate
</span>

// Hairline-bordered tile
<article className="border border-ink/12 bg-cream p-6">…</article>
```

### Pixel grid

A CSS-grid block of fixed-size cells, each cell filled with a color drawn from
the orange palette (and occasional transparent/cream cells). A few cells render
a rotated square (`rotate-45`) to read as a diamond. Implemented as a small
data-driven component in `page.tsx` (array of cell colors). Mono corner labels
(`FRONTIER AI` → here e.g. `AEO GRADER`, `AI VISIBILITY`) sit at the lower-left
and right edges.

### Corner ticks

Small `6px` black squares positioned at grid intersections of the hero graphic
(decorative registration marks). Optional, purely cosmetic.

---

## Section map (existing copy → Mistral idiom)

| # | Section | Treatment |
|---|---|---|
| 1 | Top nav | Hairline bar: `AEO Grader` wordmark, nav text, squared `Run audit` button |
| 2 | Hero | Split: giant headline left, small paragraph block right; orange pixel-grid graphic below with mono corner labels; URL form in a squared bordered card; 3-cell stats strip |
| 3 | Methodology (3 steps) | Bordered product-tile grid, each with pixel icon + step number + title + text |
| 4 | What's in the report | **Dark navy** band, centered white headline, report-signals as bordered grid |
| 5 | Who it's for + readiness | 4-up bordered column row / split with readiness card |
| 6 | Final CTA | Full-width bordered band: headline + URL form |

---

## Files

- `frontend/app/page.tsx` — rebuilt in this language (copy preserved).
- `frontend/app/page.old.tsx` — untouched backup of the previous design.
- `frontend/app/globals.css` — tokens, pixel-grid + grid-line utilities.
- `frontend/app/layout.tsx` — `next/font` for Space Grotesk + Space Mono.
- `frontend/tailwind.config.ts` — extend colors (`cream`, `ink`, `navy`,
  `orange`) and font families.
- `frontend/components/UrlForm.tsx` — restyled squared/orange (homepage-only use).
