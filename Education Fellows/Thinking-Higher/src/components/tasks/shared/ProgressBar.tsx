"use client";

import React from "react";

interface ProgressBarProps {
  current: number;
  total: number;
}

export default function ProgressBar({ current, total }: ProgressBarProps) {
  const pct = total > 0 ? (current / total) * 100 : 0;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "12px",
        padding: "8px 16px",
      }}
    >
      <span
        style={{
          fontSize: "11px",
          color: "var(--muted)",
          letterSpacing: "0.05em",
          whiteSpace: "nowrap",
          fontFamily: "'IBM Plex Mono', monospace",
        }}
      >
        Trial {current} / {total}
      </span>
      <div
        style={{
          flex: 1,
          height: "4px",
          background: "var(--surface2)",
          borderRadius: "2px",
          border: "1px solid var(--border)",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            background: "var(--accent)",
            borderRadius: "2px",
            transition: "width 0.3s ease",
          }}
        />
      </div>
    </div>
  );
}
