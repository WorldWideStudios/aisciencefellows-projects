"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";

// ── Public types (imported by wrapper files) ──────────────────────────────────

export interface MeetingLine {
  speakerId: string;   // must match a Participant.id
  text: string;
}

export interface Participant {
  id: string;
  name: string;
  title: string;
  initial: string;
  gradient: string;      // CSS gradient for avatar circle
  isFemale?: boolean;    // used for TTS voice selection
  isYou?: boolean;       // renders as the "You" tile (emoji, YOU badge, mic-off)
  gridArea?: string;     // CSS grid-area for non-standard placement
  chipColor: string;     // caption chip text colour
  chipBg: string;        // caption chip background
  chipBorder: string;    // caption chip border
  renderAvatar?: (speaking: boolean) => React.ReactNode; // optional custom SVG avatar
}

export interface MeetingTheme {
  shellBg: string;          // outer shell background
  tileBg: string;           // individual tile background
  activeColor: string;      // active speaker border + progress bar
  timerColor: string;
  textPrimary: string;
  textMuted: string;
  ctrlPrimaryBg: string;
  ctrlPrimaryColor: string;
}

export interface MeetingConfig {
  title: string;
  gridCols: string;          // CSS grid-template-columns
  gridRows: string;          // CSS grid-template-rows — use fixed px values (e.g. "120px 120px") when tiles span rows
  maxWidth?: number;         // constrain the player width (px); both configs should use the same value for visual parity
  participants: Participant[];
  lines: MeetingLine[];
  placeholderText: string;
  completionMessage: string;
  theme: MeetingTheme;
}

// ── Internal helpers ──────────────────────────────────────────────────────────

function pickVoice(voices: SpeechSynthesisVoice[], female: boolean): SpeechSynthesisVoice | null {
  const en = voices.filter((v) => v.lang.startsWith("en"));
  const femaleKw = ["female", "woman", "girl", "zira", "samantha", "victoria", "karen", "moira", "tessa", "fiona", "susan", "allison", "ava"];
  const maleKw   = ["male", "man", "guy", "david", "mark", "daniel", "alex", "tom", "james", "fred", "lee", "george", "rishi"];
  const kw = female ? femaleKw : maleKw;
  const match = en.find((v) => kw.some((k) => v.name.toLowerCase().includes(k)));
  if (match) return match;
  const google = en.filter((v) => v.name.toLowerCase().includes("google"));
  if (google.length >= 2) return google[female ? 1 : 0];
  return en[0] ?? null;
}

function WaveBar({ color }: { color: string }) {
  return (
    <div style={{ position: "absolute", bottom: 8, right: 8, display: "flex", alignItems: "flex-end", gap: 2, height: 18 }}>
      {[0, 0.1, 0.2, 0.15, 0.05].map((delay, i) => (
        <div key={i} style={{ width: 3, background: color, borderRadius: 2, animation: `vmWave 0.65s ease-in-out infinite ${delay}s` }} />
      ))}
      <style>{`@keyframes vmWave { 0%,100%{height:3px;} 50%{height:16px;} }`}</style>
    </div>
  );
}

// ── Tile renderer ─────────────────────────────────────────────────────────────

function Tile({
  participant, active, theme, userName, userIcon,
}: {
  participant: Participant;
  active: boolean;
  theme: MeetingTheme;
  userName: string;
  userIcon: string;
}) {
  const { isYou, renderAvatar, gradient, initial, name, title, gridArea } = participant;
  const displayName = isYou ? userName : name;

  return (
    <div style={{
      gridArea,
      aspectRatio: gridArea ? undefined : "16/9",
      background: theme.tileBg,
      borderRadius: 10,
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      position: "relative",
      border: `2px solid ${active ? theme.activeColor : "transparent"}`,
      transition: "border-color 0.25s ease",
    }}>
      {/* Avatar */}
      {isYou ? (
        <div style={{ fontSize: 32, marginBottom: 6, filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.3))" }}>{userIcon}</div>
      ) : renderAvatar ? (
        renderAvatar(active)
      ) : (
        <div style={{
          width: gridArea ? 68 : 52,
          height: gridArea ? 68 : 52,
          borderRadius: "50%",
          background: gradient,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: gridArea ? 24 : 18,
          fontWeight: 700,
          color: "white",
          marginBottom: 6,
          boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
        }}>{initial}</div>
      )}

      {/* Name + title (shown below avatar for non-SVG tiles) */}
      {!renderAvatar && (
        <>
          <div style={{ fontSize: 11, fontWeight: 600, color: theme.textPrimary, marginBottom: 2 }}>{displayName}</div>
          <div style={{ fontSize: 10, color: theme.textMuted }}>{isYou ? title : title}</div>
        </>
      )}

      {/* Bottom name tag (always shown) */}
      <div style={{
        position: "absolute",
        bottom: renderAvatar ? 34 : 8,
        left: 8,
        background: "rgba(0,0,0,0.65)",
        color: "#e8e8e8",
        fontSize: 11,
        fontWeight: 500,
        padding: "2px 8px",
        borderRadius: 4,
      }}>
        {displayName}{!isYou && ` · ${title}`}
      </div>

      {/* YOU badge + mic-off */}
      {isYou && (
        <>
          <div style={{ position: "absolute", top: 8, right: 8, background: "rgba(24,95,165,0.85)", color: "#B5D4F4", fontSize: 10, fontWeight: 500, padding: "2px 7px", borderRadius: 4 }}>You</div>
          <div style={{ position: "absolute", top: 8, left: 8, background: "rgba(0,0,0,0.5)", width: 22, height: 22, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>🔇</div>
        </>
      )}

      {active && !isYou && <WaveBar color={theme.activeColor} />}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface VideoMeetingPlayerProps {
  config: MeetingConfig;
  onComplete: () => void;
  userName?: string;
  userIcon?: string;
}

export default function VideoMeetingPlayer({
  config,
  onComplete,
  userName = "You",
  userIcon = "🧑‍💻",
}: VideoMeetingPlayerProps) {
  const { lines, participants, theme } = config;

  const [current, setCurrent]   = useState(-1);
  const [playing, setPlaying]   = useState(false);
  const [done, setDone]         = useState(false);
  const [elapsed, setElapsed]   = useState(0);

  const autoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tickRef      = useRef<ReturnType<typeof setInterval> | null>(null);
  const synthRef     = useRef<SpeechSynthesis | null>(null);
  const voicesRef    = useRef<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    synthRef.current = window.speechSynthesis;
    const load = () => { voicesRef.current = window.speechSynthesis.getVoices(); };
    load();
    window.speechSynthesis.addEventListener("voiceschanged", load);
    return () => {
      synthRef.current?.cancel();
      window.speechSynthesis.removeEventListener("voiceschanged", load);
      if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
      if (tickRef.current) clearInterval(tickRef.current);
    };
  }, []);

  const stopPlay = useCallback(() => {
    setPlaying(false);
    synthRef.current?.cancel();
    if (autoTimerRef.current) clearTimeout(autoTimerRef.current);
    if (tickRef.current) clearInterval(tickRef.current);
  }, []);

  const speakAndAdvance = useCallback((idx: number) => {
    setCurrent(idx);
    const line = lines[idx];
    const participant = participants.find((p) => p.id === line.speakerId);
    synthRef.current?.cancel();
    const utt = new SpeechSynthesisUtterance(line.text);
    utt.rate = 0.92;
    const isFemale = participant?.isFemale ?? false;
    utt.pitch = isFemale ? 1.1 : 0.88;
    const voice = pickVoice(voicesRef.current, isFemale);
    if (voice) utt.voice = voice;
    utt.onend = () => {
      const next = idx + 1;
      if (next < lines.length) autoTimerRef.current = setTimeout(() => speakAndAdvance(next), 300);
      else { stopPlay(); setDone(true); }
    };
    utt.onerror = () => {
      const next = idx + 1;
      if (next < lines.length) autoTimerRef.current = setTimeout(() => speakAndAdvance(next), 2000);
      else { stopPlay(); setDone(true); }
    };
    synthRef.current?.speak(utt);
  }, [lines, participants, stopPlay]);

  const togglePlay = useCallback(() => {
    if (playing) { stopPlay(); return; }
    setPlaying(true);
    const startIdx = current < 0 || current >= lines.length - 1 ? 0 : current;
    speakAndAdvance(startIdx);
    tickRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
  }, [playing, current, lines.length, speakAndAdvance, stopPlay]);

  const step = useCallback((dir: number) => {
    stopPlay();
    const next = current + dir;
    if (next >= 0 && next < lines.length) setCurrent(next);
  }, [current, lines.length, stopPlay]);

  const timerStr = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;
  const activeLine  = current >= 0 ? lines[current] : null;
  const activeP     = activeLine ? participants.find((p) => p.id === activeLine.speakerId) : null;

  return (
    <div style={{ width: "100%" }}>
      <div style={{ background: theme.shellBg, borderRadius: 12, padding: 12 }}>

        {/* Top bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 4px 10px" }}>
          <span style={{ color: theme.textPrimary, fontSize: 13, fontWeight: 500 }}>
            <span style={{ display: "inline-block", width: 8, height: 8, background: theme.activeColor, borderRadius: "50%", marginRight: 6, animation: "vmPulse 1.5s ease-in-out infinite" }} />
            {config.title}
          </span>
          <span style={{ color: theme.timerColor, fontSize: 12 }}>{timerStr}</span>
          <style>{`@keyframes vmPulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>
        </div>

        {/* Participant grid */}
        <div style={{
          display: "grid",
          gridTemplateColumns: config.gridCols,
          gridTemplateRows: config.gridRows,
          gap: 6,
        }}>
          {participants.map((p) => (
            <Tile
              key={p.id}
              participant={p}
              active={activeLine?.speakerId === p.id}
              theme={theme}
              userName={userName}
              userIcon={userIcon}
            />
          ))}
        </div>

        {/* Caption bar */}
        <div style={{ marginTop: 10, background: "#111113", borderRadius: 6, minHeight: 60, padding: "10px 14px", display: "flex", alignItems: "flex-start", gap: 10 }}>
          {activeP ? (
            <>
              <span style={{
                fontSize: 10, fontWeight: 700, padding: "2px 9px", borderRadius: 20,
                flexShrink: 0, marginTop: 1,
                textTransform: "uppercase", letterSpacing: "0.05em",
                color: activeP.chipColor,
                background: activeP.chipBg,
                border: `1px solid ${activeP.chipBorder}`,
              }}>
                {activeP.name}
              </span>
              <span style={{ fontSize: 12.5, color: theme.textPrimary, lineHeight: 1.55, flex: 1 }}>
                {activeLine!.text}
              </span>
            </>
          ) : (
            <span style={{ fontSize: 12, color: theme.textMuted, flex: 1 }}>{config.placeholderText}</span>
          )}
        </div>

        {/* Progress bar */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, padding: "0 2px" }}>
          <div style={{ flex: 1, height: 3, background: "#3a3a3e", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", background: theme.activeColor, borderRadius: 2, width: `${((current + 1) / lines.length) * 100}%`, transition: "width 0.4s linear" }} />
          </div>
          <span style={{ fontSize: 11, color: theme.timerColor, minWidth: 40, textAlign: "right" }}>
            {Math.max(0, current + 1)} / {lines.length}
          </span>
        </div>

        {/* Controls */}
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 10, marginTop: 10, paddingBottom: 2 }}>
          <button onClick={() => step(-1)} disabled={current <= 0} style={ctrlBtnStyle(false, theme)}>← Prev</button>
          <button onClick={togglePlay} style={ctrlBtnStyle(true, theme)}>{playing ? "⏸ Pause" : "▶ Play"}</button>
          <button onClick={() => step(1)} disabled={current >= lines.length - 1} style={ctrlBtnStyle(false, theme)}>Next →</button>
        </div>
      </div>

      {/* Continue */}
      {(done || current === lines.length - 1) && (
        <div style={{ marginTop: 20, textAlign: "center" }}>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>{config.completionMessage}</p>
          <button className="start-btn" onClick={onComplete} style={{ fontSize: 13 }}>Continue →</button>
        </div>
      )}
    </div>
  );
}

function ctrlBtnStyle(primary: boolean, theme: MeetingTheme): React.CSSProperties {
  return {
    background: primary ? theme.ctrlPrimaryBg : "#3a3a3e",
    border: "none",
    borderRadius: 6,
    color: primary ? theme.ctrlPrimaryColor : "#d0d0d0",
    fontSize: 12,
    fontWeight: 500,
    padding: "7px 18px",
    cursor: "pointer",
    fontFamily: "inherit",
  };
}
