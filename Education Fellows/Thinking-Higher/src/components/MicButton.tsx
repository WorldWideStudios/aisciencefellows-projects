"use client";

export type MicState = "idle" | "listening";

interface MicButtonProps {
  state: MicState;
  onClick: () => void;
  disabled?: boolean;
}

function MicIcon() {
  return (
    <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="2" width="6" height="12" rx="3" />
      <path d="M5 10a7 7 0 0 0 14 0" />
      <line x1="12" y1="20" x2="12" y2="23" />
      <line x1="9"  y1="23" x2="15" y2="23" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="3" />
    </svg>
  );
}

export default function MicButton({ state, onClick, disabled }: MicButtonProps) {
  return (
    <button
      className={`mic-btn mic-btn--${state}`}
      onClick={onClick}
      disabled={disabled}
      aria-label={state === "idle" ? "Start speaking" : "Stop recording"}
    >
      {state === "idle"      && <MicIcon />}
      {state === "listening" && <StopIcon />}
      {state === "listening" && <span className="mic-pulse-ring" />}
      {state === "listening" && <span className="mic-pulse-ring mic-pulse-ring--delay" />}
    </button>
  );
}
