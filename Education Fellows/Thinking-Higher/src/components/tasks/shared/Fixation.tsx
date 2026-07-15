"use client";

import React, { useEffect } from "react";

interface FixationProps {
  durationMs: number;
  onComplete: () => void;
}

export default function Fixation({ durationMs, onComplete }: FixationProps) {
  useEffect(() => {
    const timer = setTimeout(onComplete, durationMs);
    return () => clearTimeout(timer);
  }, [durationMs, onComplete]);

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        width: "100%",
        height: "100%",
        position: "absolute",
        inset: 0,
      }}
    >
      <span
        style={{
          fontSize: "48px",
          fontWeight: 300,
          color: "var(--text)",
          userSelect: "none",
          fontFamily: "'IBM Plex Mono', monospace",
        }}
      >
        +
      </span>
    </div>
  );
}
