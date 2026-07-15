# AOS Landing Restructure — Design Spec

**Date:** 2026-05-29
**Status:** Approved structure, copy TBD
**Scope:** Homepage (`frontend/app/page.tsx`) only.

## Goal

Make the **Agent Operability Score (AOS)** the site's main and only public feature.
The homepage `/` is rebuilt to sell and launch AOS. The existing AEO Grader landing
is removed from routing but preserved as a non-routed backup. The polished
Mistral-style visual language (cream/orange/pixel-grid, squared corners, hairline
grid, one dark navy band) is **reused** — only structure and copy change.

## What AOS measures

A 0–100 score across 4 blocks (all treated as **live** on the landing):

| Block | Pts | Signals |
|---|---|---|
| Machine Interface | 30 | MCP servers, OpenAPI specs |
| Browser Operability | 25 | (now working — no longer a stub) |
| Agent Discovery | 25 | llms.txt, robots.txt, Schema.org |
| Auth & Security | 20 | OAuth, CORS |

> Note: `CLAUDE.md` still describes Browser Operability as a stub. The user
> confirms it is fixed; landing treats it as live. Update `CLAUDE.md` separately.

## Core narrative

SEO/AEO got you *found* by AI. **AOS measures whether an AI agent can actually
operate your platform** — discover its interfaces, authenticate, and act.
Hero concept line: *"See how agents feel when interacting with your platform."*

## Routing changes

- `/` → new AOS landing (was AEO landing).
- AEO landing removed from routing; its code preserved as `frontend/app/page.old.tsx`
  (already exists as the backup file).
- Homepage URL form routes to the existing AOS results route
  `/agent-report/[domain]` (unchanged — reuses working code).
- AOS results routes (`/agent-report/[domain]`, its `loading.tsx`) unchanged.
- AEO results routes (`/report/[id]`, `/analyze/[id]`) left intact but unlinked.

## Section blueprint (Option B — agent-narrative)

Reuses existing components: hero split + `PixelHero`, bordered tile grid,
dark navy signals band, readiness card, CTA band, footer.

1. **Nav** — hairline bar. AOS wordmark/glyph + name; anchor nav links
   (The shift · Scoring · Report · FAQ); squared "Run scan" CTA → hero form.
2. **Hero** — eyebrow micro-label; giant headline (*"See how agents feel when
   interacting with your platform."*); short paragraph; URL form card → AOS
   results; 3-cell stat strip (`0–100` score · `4` blocks · `~30s` scan);
   `PixelHero` graphic with floating card repurposed to show a sample capability
   probe (e.g. MCP endpoint / OpenAPI detected) instead of source bars.
3. **"The Shift" band** (new, light, bordered) — eyebrow + headline
   (visibility ≠ operability); 2-column contrast: AEO/SEO = can agents *find* you
   → AOS = can agents *use* you.
4. **The 4 Scoring Blocks** (centerpiece — bordered tile grid) — eyebrow +
   headline; 4 tiles each with block name, point value, 1-line description, pixel
   glyph: Machine Interface 30 · Browser Operability 25 · Agent Discovery 25 ·
   Auth & Security 20. All shown as live.
5. **What we detect** (dark navy band — reuse signals grid) — centered white
   headline + intro; bordered grid of concrete signals: MCP servers · OpenAPI
   specs · OAuth · CORS · llms.txt · robots.txt · Schema.org · SDK docs.
6. **Who it's for + readiness card** (reuse split + card) — left: audience copy
   (API platforms, SaaS, dev tools wanting to be agent-ready); right: readiness
   card previewing a sample verdict ("Agent Ready" badge + checklist items).
7. **Final CTA + Footer** (reuse) — bordered band with headline + URL form;
   footer with wordmark + tagline.

## Copy status

Structure is approved. **Final copy is deferred** — section content slots are
defined here; exact wording is written during implementation / a later copy pass.
Only the hero concept line above is fixed.

## Out of scope

- AEO Grader backend, results pages, and any AEO-specific frontend logic.
- AOS scan/results pages and `lib/agent-check/*` logic.
- The root `design.md` (governs app/report components, unchanged).
