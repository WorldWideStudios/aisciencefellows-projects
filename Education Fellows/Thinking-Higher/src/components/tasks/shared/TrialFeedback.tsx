"use client";

import React, { useEffect } from "react";

interface TrialFeedbackProps {
  reward: boolean;
  durationMs: number;
  onComplete: () => void;
  points?: number;
}

export default function TrialFeedback({
  reward,
  durationMs,
  onComplete,
  points,
}: TrialFeedbackProps) {
  useEffect(() => {
    const timer = setTimeout(onComplete, durationMs);
    return () => clearTimeout(timer);
  }, [durationMs, onComplete]);

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        background: "rgba(13, 13, 15, 0.85)",
        zIndex: 10,
      }}
    >
      <span
        style={{
          fontSize: "56px",
          color: reward ? "var(--success)" : "var(--danger)",
          lineHeight: 1,
          userSelect: "none",
        }}
      >
        {reward ? "\u2713" : "\u2717"}
      </span>
      {reward && (
        <span
          style={{
            fontSize: "20px",
            fontWeight: 600,
            color: "var(--accent)",
            marginTop: "8px",
            fontFamily: "'Syne', sans-serif",
            letterSpacing: "0.05em",
          }}
        >
          +{points ?? 1}
        </span>
      )}
    </div>
  );
}
