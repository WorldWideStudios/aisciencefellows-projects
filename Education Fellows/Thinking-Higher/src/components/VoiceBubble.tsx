"use client";

interface VoiceBubbleProps {
  durationSec: number;
}

// Deterministic pseudo-random waveform seeded by duration
function waveHeights(durationSec: number, count = 28): number[] {
  const heights: number[] = [];
  let seed = durationSec * 1000 + 42;
  for (let i = 0; i < count; i++) {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    heights.push(20 + Math.abs(seed % 60));
  }
  return heights;
}

function formatDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default function VoiceBubble({ durationSec }: VoiceBubbleProps) {
  const bars = waveHeights(durationSec);

  return (
    <div className="voice-bubble">
      <svg className="voice-bubble-mic" width="18" height="18" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="9" y="2" width="6" height="12" rx="3" />
        <path d="M5 10a7 7 0 0 0 14 0" />
        <line x1="12" y1="20" x2="12" y2="23" />
        <line x1="9"  y1="23" x2="15" y2="23" />
      </svg>

      <div className="voice-bubble-wave">
        {bars.map((h, i) => (
          <span key={i} style={{ height: `${h}%` }} />
        ))}
      </div>

      <span className="voice-bubble-duration">{formatDuration(durationSec)}</span>
    </div>
  );
}
