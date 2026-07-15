export interface ScoreLevel {
  label: string;
  rangeStart: number;
  rangeEnd: number;
  textClass: string;
  bgClass: string;
  barClass: string;
}

const LEVELS: ScoreLevel[] = [
  { label: "Invisible to AI",    rangeStart: 0,  rangeEnd: 19,  textClass: "text-red-700",     bgClass: "bg-red-50",     barClass: "bg-red-500" },
  { label: "Weak Visibility",    rangeStart: 20, rangeEnd: 39,  textClass: "text-orange-700",  bgClass: "bg-orange-50",  barClass: "bg-orange-500" },
  { label: "Moderate Visibility",rangeStart: 40, rangeEnd: 59,  textClass: "text-yellow-700",  bgClass: "bg-yellow-50",  barClass: "bg-yellow-500" },
  { label: "Strong Visibility",  rangeStart: 60, rangeEnd: 79,  textClass: "text-green-700",   bgClass: "bg-green-50",   barClass: "bg-green-500" },
  { label: "Niche Leader",       rangeStart: 80, rangeEnd: 100, textClass: "text-emerald-800", bgClass: "bg-emerald-50", barClass: "bg-emerald-600" },
];

export function getLevel(score: number): ScoreLevel {
  const clamped = Math.max(0, Math.min(100, score));
  for (const lv of LEVELS) {
    if (clamped >= lv.rangeStart && clamped <= lv.rangeEnd) return lv;
  }
  return LEVELS[0];
}

export function getNextLevel(score: number): ScoreLevel | null {
  const current = getLevel(score);
  const idx = LEVELS.indexOf(current);
  return idx < LEVELS.length - 1 ? LEVELS[idx + 1] : null;
}

export function deltaToNextLevel(score: number): { points: number; label: string } | null {
  const next = getNextLevel(score);
  if (!next) return null;
  return { points: Math.max(0, Math.round(next.rangeStart - score)), label: next.label };
}

export function formatPercent(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export const SENTIMENT_LABEL: Record<string, string> = {
  positive: "Positive",
  neutral: "Neutral",
  mixed: "Mixed",
  negative: "Negative",
};
