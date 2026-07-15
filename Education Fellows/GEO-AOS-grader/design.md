# GEO Grader — UI Design Language

## Tech Stack — Frontend UI

- **Tailwind CSS** — no UI library (no shadcn, no MUI). All components are custom.
- No state management library — `useState`/`useEffect` only

## Design Patterns

Follow these patterns exactly when writing UI code:

```tsx
// Page wrapper
<main className="mx-auto max-w-3xl p-8">

// Cards
<div className="rounded-2xl border border-neutral-200 bg-white px-6 py-10">

// Primary button
<button className="rounded-lg bg-neutral-900 px-6 py-3 text-base font-medium text-white hover:bg-neutral-700 disabled:opacity-50">

// Text input
<input className="flex-1 rounded-lg border border-neutral-300 px-4 py-3 text-base outline-none focus:border-neutral-900">

// Secondary / muted text
<p className="text-sm text-neutral-500">
<p className="text-xs text-neutral-400">
```

Dynamic colors (grade colors, score bar colors) use `style={{ color }}` — not Tailwind classes — because the values are runtime hex strings.

## Agent Report Components

| Component | Description |
|---|---|
| `ScanProgress.tsx` | Step list, activates as SSE block events arrive |
| `ScoreHero.tsx` | Big score number + grade badge |
| `BlockCard.tsx` | Score/max + progress bar; "Coming soon" for Block 2 |
| `CheckItem.tsx` | Single check row: ✓/~/✗ icon + name + pts + evidence |
| `BlockDetail.tsx` | Accordion section with CheckItem list |
| `PendingBlock.tsx` | Block 2 "coming soon" placeholder |
| `ReportLayout.tsx` | Assembles hero + 4 cards + 3 detail sections + footer |

## Grade Colors

Grade thresholds used in `ScoreHero` and `BlockCard`:

- 0–25 → "Not Agent Ready" `#ef4444`
- 26–50 → "Early Stage" `#f97316`
- 51–75 → "Agent Friendly" `#eab308`
- 76–90 → "Agent Ready" `#22c55e`
- 91–100 → "Agent Native" `#3b82f6`
