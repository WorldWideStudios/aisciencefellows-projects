"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface MeetingLine {
  speaker: string;
  tile: "sarah" | "alex" | "marcus";
  color: string;
  text: string;
}

const LINES: MeetingLine[] = [
  {
    speaker: "Sarah",
    tile: "sarah",
    color: "#CECBF6",
    text: "Alright, let's keep this quick. Vela aims to provide IT asset management services to companies, and we want their IT admins to manage their company's IT assets as smoothly as possible. Our team's goal in this sprint is to design and develop the very first onboarding platform for the IT admins. Marcus, as our UX designer, do you want to kick us off today?",
  },
  {
    speaker: "Marcus",
    tile: "marcus",
    color: "#F5C4B3",
    text: "Yeah — so I finished up six user interviews with IT admins for designing the Vela platform onboarding module over the past week. Big takeaway: they need to see and choose what they're tracking for the company — software licenses, laptops, other devices — before the form asks for any details. They won't fill in what they didn't opt into. I also think we need to be really clear at each onboarding step about what level of detail the form is asking for; if not, people just bail.",
  },
  {
    speaker: "Sarah",
    tile: "sarah",
    color: "#CECBF6",
    text: "That tracks with what I'm hearing from the sales side too. What else?",
  },
  {
    speaker: "Marcus",
    tile: "marcus",
    color: "#F5C4B3",
    text: "One more thing — three of the six admins said they wouldn't have all their inventory info on hand during signup. So ideally, they could save progress and come back later.",
  },
  {
    speaker: "Alex",
    tile: "alex",
    color: "#C0DD97",
    text: "The first two are fine — we can build that. The save-and-return piece is a different story. Persisting draft state server-side isn't trivial. I don't think we can scope that into one sprint without it becoming the whole sprint.",
  },
  {
    speaker: "Sarah",
    tile: "sarah",
    color: "#CECBF6",
    text: "Noted. Let's park that and focus on the first two. Alex, anything else from you?",
  },
  {
    speaker: "Alex",
    tile: "alex",
    color: "#C0DD97",
    text: "Just one thing — I want to flag for the team that the junior software engineer in our team is going to be taking the lead on building the onboarding module.",
  },
  {
    speaker: "Sarah",
    tile: "sarah",
    color: "#CECBF6",
    text: "Great. Welcome to the project officially. Please sync later with Marcus to discuss the design and development in detail for this week's sprint.",
  },
  {
    speaker: "Marcus",
    tile: "marcus",
    color: "#F5C4B3",
    text: "Sure thing — let's talk tomorrow after I have the prototype fleshed out!",
  },
];

// SVG avatars
function SarahAvatar({ speaking }: { speaking: boolean }) {
  return (
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ width: 56, height: 56, borderRadius: "50%", filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.3))" }}>
      <circle cx="50" cy="50" r="50" fill="#3C3489"/>
      <ellipse cx="50" cy="72" rx="26" ry="18" fill="#2a2370"/>
      <ellipse cx="50" cy="40" rx="18" ry="17" fill="#f5c8b0"/>
      <ellipse cx="50" cy="26" rx="18" ry="11" fill="#3d2314"/>
      <ellipse cx="34" cy="34" rx="6" ry="10" fill="#3d2314"/>
      <ellipse cx="66" cy="34" rx="6" ry="10" fill="#3d2314"/>
      <rect x="32" y="22" width="36" height="10" rx="5" fill="#3d2314"/>
      <ellipse cx="43" cy="40" rx="3" ry="3.5" fill="#fff"/>
      <ellipse cx="57" cy="40" rx="3" ry="3.5" fill="#fff"/>
      <circle cx="43" cy="40" r="1.8" fill="#4a3000"/>
      <circle cx="57" cy="40" r="1.8" fill="#4a3000"/>
      {speaking ? (
        <ellipse cx="50" cy="52" rx="5" ry="3.5" fill="#8B2020"/>
      ) : (
        <path d="M44 50 Q50 54 56 50" stroke="#c0785a" strokeWidth="1.5" fill="none" strokeLinecap="round"/>
      )}
      <path d="M24 90 Q50 78 76 90 L76 100 L24 100 Z" fill="#5a4faa"/>
    </svg>
  );
}

function AlexAvatar({ speaking }: { speaking: boolean }) {
  return (
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ width: 56, height: 56, borderRadius: "50%", filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.3))" }}>
      <circle cx="50" cy="50" r="50" fill="#2a3a28"/>
      <ellipse cx="50" cy="74" rx="28" ry="18" fill="#1e2e1c"/>
      <ellipse cx="50" cy="40" rx="18" ry="17" fill="#d4956a"/>
      <ellipse cx="50" cy="25" rx="18" ry="10" fill="#1a1008"/>
      <rect x="32" y="22" width="36" height="8" rx="4" fill="#1a1008"/>
      <ellipse cx="43" cy="39" rx="3" ry="3.2" fill="#fff"/>
      <ellipse cx="57" cy="39" rx="3" ry="3.2" fill="#fff"/>
      <circle cx="43" cy="39" r="1.8" fill="#2a1800"/>
      <circle cx="57" cy="39" r="1.8" fill="#2a1800"/>
      <path d="M39 34 Q43 33 47 34" stroke="#1a1008" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
      <path d="M53 34 Q57 33 61 34" stroke="#1a1008" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
      {speaking ? (
        <ellipse cx="50" cy="53" rx="5.5" ry="3" fill="#7a2a10"/>
      ) : (
        <path d="M43 50 Q50 56 57 50" stroke="#b06040" strokeWidth="1.6" fill="none" strokeLinecap="round"/>
      )}
      <path d="M24 92 Q50 78 76 92 L76 100 L24 100 Z" fill="#2c3e50"/>
    </svg>
  );
}

function MarcusAvatar({ speaking }: { speaking: boolean }) {
  return (
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" style={{ width: 56, height: 56, borderRadius: "50%", filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.3))" }}>
      <circle cx="50" cy="50" r="50" fill="#5a3010"/>
      <ellipse cx="50" cy="73" rx="27" ry="18" fill="#3e1e08"/>
      <ellipse cx="50" cy="40" rx="18" ry="18" fill="#8B5E3C"/>
      <ellipse cx="50" cy="22" rx="20" ry="12" fill="#1a0800"/>
      <circle cx="34" cy="28" r="8" fill="#1a0800"/>
      <circle cx="66" cy="28" r="8" fill="#1a0800"/>
      <circle cx="50" cy="18" r="8" fill="#1a0800"/>
      <ellipse cx="43" cy="40" rx="3" ry="3.5" fill="#fff"/>
      <ellipse cx="57" cy="40" rx="3" ry="3.5" fill="#fff"/>
      <circle cx="43" cy="40" r="2" fill="#2a1500"/>
      <circle cx="57" cy="40" r="2" fill="#2a1500"/>
      <rect x="37" y="36" width="10" height="8" rx="3" fill="none" stroke="#555" strokeWidth="1.2"/>
      <rect x="53" y="36" width="10" height="8" rx="3" fill="none" stroke="#555" strokeWidth="1.2"/>
      <line x1="47" y1="40" x2="53" y2="40" stroke="#555" strokeWidth="1.2"/>
      {speaking ? (
        <ellipse cx="50" cy="54" rx="5.5" ry="3.5" fill="#5a1a00"/>
      ) : (
        <path d="M43 51 Q50 57 57 51" stroke="#7a3a1a" strokeWidth="1.8" fill="none" strokeLinecap="round"/>
      )}
      <path d="M23 92 Q50 78 77 92 L77 100 L23 100 Z" fill="#993C1D"/>
    </svg>
  );
}

function YouAvatar({ icon }: { icon: string }) {
  return (
    <div style={{
      width: 56, height: 56, borderRadius: "50%",
      background: "#185FA5",
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 28,
      filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.3))",
      flexShrink: 0,
    }}>
      {icon}
    </div>
  );
}

interface VideoMeetingProps {
  onComplete: () => void;
  userName?: string;
  userIcon?: string;
}

// Pick best available voice for a given gender preference
function pickVoice(voices: SpeechSynthesisVoice[], female: boolean): SpeechSynthesisVoice | null {
  const enVoices = voices.filter((v) => v.lang.startsWith("en"));
  // Prefer voices whose names suggest the right gender
  const femaleKeywords = ["female", "woman", "girl", "zira", "samantha", "victoria", "karen", "moira", "tessa", "fiona", "susan", "allison", "ava"];
  const maleKeywords = ["male", "man", "guy", "david", "mark", "daniel", "alex", "tom", "james", "fred", "lee", "george", "rishi"];
  const keywords = female ? femaleKeywords : maleKeywords;
  const match = enVoices.find((v) => keywords.some((k) => v.name.toLowerCase().includes(k)));
  if (match) return match;
  // Fallback: Google voices tend to come in pairs; pick second (index 1) for female
  const googleEn = enVoices.filter((v) => v.name.toLowerCase().includes("google"));
  if (googleEn.length >= 2) return googleEn[female ? 1 : 0];
  return enVoices[0] ?? null;
}

export default function VideoMeeting({ onComplete, userName = "You", userIcon = "🧑‍💻" }: VideoMeetingProps) {
  const [current, setCurrent] = useState(-1);
  const [playing, setPlaying] = useState(false);
  const [done, setDone] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const autoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const synthRef = useRef<SpeechSynthesis | null>(null);
  const voicesRef = useRef<SpeechSynthesisVoice[]>([]);

  useEffect(() => {
    if (typeof window === "undefined") return;
    synthRef.current = window.speechSynthesis;
    const loadVoices = () => { voicesRef.current = window.speechSynthesis.getVoices(); };
    loadVoices();
    window.speechSynthesis.addEventListener("voiceschanged", loadVoices);
    return () => {
      synthRef.current?.cancel();
      window.speechSynthesis.removeEventListener("voiceschanged", loadVoices);
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
    const line = LINES[idx];
    synthRef.current?.cancel();
    const utt = new SpeechSynthesisUtterance(line.text);
    utt.rate = 0.92;
    const isFemale = line.tile === "sarah";
    utt.pitch = isFemale ? 1.1 : 0.88;
    const voice = pickVoice(voicesRef.current, isFemale);
    if (voice) utt.voice = voice;
    utt.onend = () => {
      const next = idx + 1;
      if (next < LINES.length) {
        autoTimerRef.current = setTimeout(() => speakAndAdvance(next), 300);
      } else {
        stopPlay();
        setDone(true);
      }
    };
    utt.onerror = () => {
      const next = idx + 1;
      if (next < LINES.length) {
        autoTimerRef.current = setTimeout(() => speakAndAdvance(next), 2000);
      } else {
        stopPlay();
        setDone(true);
      }
    };
    synthRef.current?.speak(utt);
  }, [stopPlay]);

  const togglePlay = useCallback(() => {
    if (playing) {
      stopPlay();
      return;
    }
    setPlaying(true);
    const startIdx = current < 0 || current >= LINES.length - 1 ? 0 : current;
    speakAndAdvance(startIdx);
    tickRef.current = setInterval(() => setElapsed((e) => e + 1), 1000);
  }, [playing, current, speakAndAdvance, stopPlay]);

  const step = useCallback((dir: number) => {
    stopPlay();
    const next = current + dir;
    if (next >= 0 && next < LINES.length) setCurrent(next);
  }, [current, stopPlay]);

  const timerStr = `${String(Math.floor(elapsed / 60)).padStart(2, "0")}:${String(elapsed % 60).padStart(2, "0")}`;
  const activeLine = current >= 0 ? LINES[current] : null;

  const tileStyle = (tile: string): React.CSSProperties => ({
    background: "#2a2a2e",
    borderRadius: 8,
    position: "relative",
    overflow: "hidden",
    aspectRatio: "16/9",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    border: `2px solid ${activeLine?.tile === tile ? "#1D9E75" : "transparent"}`,
    transition: "border-color 0.25s ease",
  });

  return (
    <div style={{ width: "100%" }}>
      {/* Zoom shell */}
      <div style={{ background: "#1c1c1e", borderRadius: 12, padding: 12 }}>
        {/* Top bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 4px 10px" }}>
          <span style={{ color: "#e0e0e0", fontSize: 13, fontWeight: 500 }}>
            <span style={{ display: "inline-block", width: 8, height: 8, background: "#e24b4a", borderRadius: "50%", marginRight: 6 }} />
            Vela — Monday Group Meeting
          </span>
          <span style={{ color: "#888", fontSize: 12 }}>{timerStr}</span>
        </div>

        {/* 2x2 grid */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
          {/* Sarah */}
          <div style={tileStyle("sarah")}>
            <SarahAvatar speaking={activeLine?.tile === "sarah"} />
            <div style={{ position: "absolute", bottom: 34, left: 8, background: "rgba(0,0,0,0.65)", color: "#e8e8e8", fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 4 }}>Sarah · Project Manager</div>
            {activeLine?.tile === "sarah" && <WaveBar />}
          </div>
          {/* Alex */}
          <div style={tileStyle("alex")}>
            <AlexAvatar speaking={activeLine?.tile === "alex"} />
            <div style={{ position: "absolute", bottom: 34, left: 8, background: "rgba(0,0,0,0.65)", color: "#e8e8e8", fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 4 }}>Alex · Tech Lead</div>
            {activeLine?.tile === "alex" && <WaveBar />}
          </div>
          {/* Marcus */}
          <div style={tileStyle("marcus")}>
            <MarcusAvatar speaking={activeLine?.tile === "marcus"} />
            <div style={{ position: "absolute", bottom: 34, left: 8, background: "rgba(0,0,0,0.65)", color: "#e8e8e8", fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 4 }}>Marcus · UX Designer</div>
            {activeLine?.tile === "marcus" && <WaveBar />}
          </div>
          {/* You */}
          <div style={tileStyle("you")}>
            <YouAvatar icon={userIcon} />
            <div style={{ position: "absolute", bottom: 34, left: 8, background: "rgba(0,0,0,0.65)", color: "#e8e8e8", fontSize: 11, fontWeight: 500, padding: "2px 8px", borderRadius: 4 }}>{userName} · Junior SDE</div>
            <div style={{ position: "absolute", top: 8, right: 8, background: "rgba(24,95,165,0.85)", color: "#B5D4F4", fontSize: 10, fontWeight: 500, padding: "2px 7px", borderRadius: 4 }}>You</div>
          </div>
        </div>

        {/* Caption bar */}
        <div style={{ marginTop: 10, background: "#111113", borderRadius: 6, minHeight: 60, padding: "10px 14px", display: "flex", alignItems: "flex-start", gap: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 500, whiteSpace: "nowrap", paddingTop: 1, minWidth: 52, color: activeLine?.color ?? "#666" }}>
            {activeLine?.speaker ?? "—"}
          </span>
          <span style={{ fontSize: 12, color: "#c8c8cc", lineHeight: 1.55, flex: 1 }}>
            {activeLine?.text ?? "Press play to start the meeting."}
          </span>
        </div>

        {/* Progress */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, padding: "0 2px" }}>
          <div style={{ flex: 1, height: 3, background: "#3a3a3e", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", background: "#1D9E75", borderRadius: 2, width: `${((current + 1) / LINES.length) * 100}%`, transition: "width 0.4s linear" }} />
          </div>
          <span style={{ fontSize: 11, color: "#666", minWidth: 40, textAlign: "right" }}>{Math.max(0, current + 1)} / {LINES.length}</span>
        </div>

        {/* Controls */}
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 10, marginTop: 10, paddingBottom: 2 }}>
          <button onClick={() => step(-1)} disabled={current <= 0} style={ctrlBtnStyle(false)}>← Prev</button>
          <button onClick={togglePlay} style={ctrlBtnStyle(true)}>{playing ? "⏸ Pause" : "▶ Play"}</button>
          <button onClick={() => step(1)} disabled={current >= LINES.length - 1} style={ctrlBtnStyle(false)}>Next →</button>
        </div>
      </div>

      {/* Continue button — shown when last line reached or TTS finishes */}
      {(done || current === LINES.length - 1) && (
        <div style={{ marginTop: 20, textAlign: "center" }}>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>
            Meeting complete. Sarah will ask if you have any questions.
          </p>
          <button className="start-btn" onClick={onComplete} style={{ fontSize: 13 }}>
            Continue to Q&A →
          </button>
        </div>
      )}
    </div>
  );
}

function WaveBar() {
  return (
    <div style={{ position: "absolute", bottom: 10, right: 10, display: "flex", alignItems: "flex-end", gap: 2, height: 20 }}>
      {[0, 0.1, 0.2, 0.15, 0.05].map((delay, i) => (
        <div key={i} style={{ width: 3, background: "#1D9E75", borderRadius: 2, animation: `waveBar 0.65s ease-in-out infinite ${delay}s` }} />
      ))}
      <style>{`
        @keyframes waveBar {
          0%, 100% { height: 3px; }
          50% { height: 18px; }
        }
      `}</style>
    </div>
  );
}

function ctrlBtnStyle(primary: boolean): React.CSSProperties {
  return {
    background: primary ? "#1D9E75" : "#3a3a3e",
    border: "none",
    borderRadius: 6,
    color: "#d0d0d0",
    fontSize: 12,
    fontWeight: 500,
    padding: "7px 18px",
    cursor: "pointer",
    fontFamily: "inherit",
  };
}
