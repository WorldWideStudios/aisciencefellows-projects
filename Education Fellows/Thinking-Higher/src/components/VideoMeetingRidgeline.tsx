"use client";

import { useState, useEffect, useRef, useCallback } from "react";

interface MeetingLine {
  speaker: "jordan" | "priya" | "derek";
  name: string;
  text: string;
}

const LINES: MeetingLine[] = [
  {
    speaker: "jordan",
    name: "Jordan",
    text: "Alright, let's get into it. Priya flagged something to me last week that I think we need to get eyes on before planning season starts. I'm not going to sugarcoat it — the numbers aren't trending in the right direction, and the board is asking questions I don't have good answers to yet.",
  },
  {
    speaker: "priya",
    name: "Priya",
    text: "Yeah. I've been sitting with the budget actuals for a few weeks now. It's not a crisis yet, but the direction is — it's not great.",
  },
  {
    speaker: "jordan",
    name: "Jordan",
    text: "Right. So here's what we're doing. I've asked our new Analyst to come in fresh and take a real look — budget, enrollment, the works. No preconceptions. Priya, you'll walk them through the financials. Derek, enrollment data on your end.",
  },
  {
    speaker: "derek",
    name: "Derek",
    text: "Sure — I can pull the last three years broken out by program. Full-time, part-time, the whole picture.",
  },
  {
    speaker: "jordan",
    name: "Jordan",
    text: "Good. And I want to be clear about one thing — you two are there to share the data and answer questions about what's in it. The interpretation, the 'so what' — that's our Analyst's job. I don't want the answer pre-baked before it gets to me.",
  },
  {
    speaker: "priya",
    name: "Priya",
    text: "Fair enough. I'll keep my opinions to myself.",
  },
  {
    speaker: "jordan",
    name: "Jordan",
    text: "One thing you need to know going in: the board has been explicit with me. We need to be back in surplus within two fiscal years, and reserves don't go below three million. That's not a goal — that's a constraint. Whatever you bring back to me has to work inside those guardrails.",
  },
  {
    speaker: "derek",
    name: "Derek",
    text: "That's a tight window.",
  },
  {
    speaker: "jordan",
    name: "Jordan",
    text: "It is. Which is why I need someone looking at this without any of the baggage the rest of us are carrying. Alright — Priya, you'll connect with our Analyst first. Derek, you're after. Let's get moving.",
  },
];

const SPEAKER_COLORS: Record<string, string> = {
  jordan: "#2563eb",
  priya: "#7c3aed",
  derek: "#059669",
};

function pickVoice(voices: SpeechSynthesisVoice[], female: boolean): SpeechSynthesisVoice | null {
  const enVoices = voices.filter((v) => v.lang.startsWith("en"));
  const femaleKw = ["female", "woman", "girl", "zira", "samantha", "victoria", "karen", "moira", "tessa", "fiona", "susan", "allison", "ava"];
  const maleKw = ["male", "man", "guy", "david", "mark", "daniel", "alex", "tom", "james", "fred", "lee", "george", "rishi"];
  const kw = female ? femaleKw : maleKw;
  const match = enVoices.find((v) => kw.some((k) => v.name.toLowerCase().includes(k)));
  if (match) return match;
  const googleEn = enVoices.filter((v) => v.name.toLowerCase().includes("google"));
  if (googleEn.length >= 2) return googleEn[female ? 1 : 0];
  return enVoices[0] ?? null;
}

function WaveBar() {
  return (
    <div style={{ position: "absolute", bottom: 8, right: 8, display: "flex", alignItems: "flex-end", gap: 2, height: 16 }}>
      {[0, 0.1, 0.2, 0.15, 0.05].map((delay, i) => (
        <div key={i} style={{ width: 3, background: "#4ade80", borderRadius: 2, animation: `waveBarR 0.65s ease-in-out infinite ${delay}s` }} />
      ))}
      <style>{`@keyframes waveBarR { 0%,100%{height:3px;} 50%{height:14px;} }`}</style>
    </div>
  );
}

function AvatarTile({
  id, initial, name, title, large, active, colorClass, userIcon, userName,
}: {
  id: string; initial?: string; name: string; title: string;
  large?: boolean; active: boolean; colorClass?: string;
  userIcon?: string; userName?: string;
}) {
  const gradients: Record<string, string> = {
    jordan: "linear-gradient(135deg, #1a3260, #2e75b6)",
    priya:  "linear-gradient(135deg, #a78bfa, #7c3aed)",
    derek:  "linear-gradient(135deg, #0e6670, #14b8a6)",
    you:    "linear-gradient(135deg, #f4a261, #e76f51)",
  };
  const isYou = id === "you";
  const gridArea = large ? "1 / 1 / 3 / 2" : undefined;

  return (
    <div style={{
      gridArea,
      background: "#112240",
      borderRadius: 10,
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      position: "relative",
      border: `1.5px solid ${active ? "#4ade80" : "transparent"}`,
      transition: "border-color 0.3s",
    }}>
      <div style={{
        width: large ? 68 : 52,
        height: large ? 68 : 52,
        borderRadius: "50%",
        background: gradients[id] ?? gradients.you,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: isYou ? (large ? 30 : 24) : (large ? 24 : 18),
        fontWeight: 700,
        color: "white",
        marginBottom: 8,
        boxShadow: "0 4px 16px rgba(0,0,0,0.3)",
      }}>
        {isYou ? (userIcon ?? "🧑‍💻") : initial}
      </div>
      <div style={{ fontSize: 11, fontWeight: 600, color: "#e0eaf8", marginBottom: 2 }}>{isYou ? (userName ?? "You") : name}</div>
      <div style={{ fontSize: 10, color: "#7a96b8" }}>{title}</div>
      <div style={{
        position: "absolute", bottom: 8, left: 10,
        background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)",
        padding: "3px 8px", borderRadius: 5,
        fontSize: 10.5, fontWeight: 500, color: "white",
        display: "flex", alignItems: "center", gap: 5,
      }}>
        {active && "🎙 "}{isYou ? (userName ?? "You") : name}
      </div>
      {isYou && (
        <>
          <div style={{
            position: "absolute", top: 8, right: 8,
            background: "#1a3260", color: "white",
            fontSize: 9, fontWeight: 700, padding: "2px 7px", borderRadius: 4,
            letterSpacing: "0.05em", textTransform: "uppercase",
          }}>YOU</div>
          <div style={{
            position: "absolute", top: 8, left: 8,
            background: "rgba(0,0,0,0.5)",
            width: 22, height: 22, borderRadius: "50%",
            display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11,
          }}>🔇</div>
        </>
      )}
      {active && !isYou && <WaveBar />}
    </div>
  );
}

interface VideoMeetingRidgelineProps {
  onComplete: () => void;
  userName?: string;
  userIcon?: string;
}

export default function VideoMeetingRidgeline({ onComplete, userName = "You", userIcon = "🧑‍💻" }: VideoMeetingRidgelineProps) {
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
    const isFemale = line.speaker === "priya";
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
    if (playing) { stopPlay(); return; }
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

  return (
    <div style={{ width: "100%" }}>
      {/* Meeting shell — dark navy */}
      <div style={{ background: "#0d1b2a", borderRadius: 12, padding: 12 }}>
        {/* Top bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 4px 10px" }}>
          <span style={{ color: "#e0eaf8", fontSize: 13, fontWeight: 600, fontFamily: "inherit" }}>
            <span style={{ display: "inline-block", width: 8, height: 8, background: "#4ade80", borderRadius: "50%", marginRight: 6, animation: "pulse 1.5s ease-in-out infinite" }} />
            Ridgeline CC — Office of the President
          </span>
          <span style={{ color: "#7a96b8", fontSize: 12, fontFamily: "monospace" }}>{timerStr}</span>
          <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }`}</style>
        </div>

        {/* Video grid — Jordan large (left, spans 2 rows), Priya/Derek/You on right */}
        <div style={{
          display: "grid",
          gridTemplateColumns: "1.6fr 1fr 1fr",
          gridTemplateRows: "1fr 1fr",
          gap: 6,
          height: 240,
        }}>
          <AvatarTile id="jordan" initial="J" name="Jordan Ellis" title="Chief of Staff" large active={activeLine?.speaker === "jordan"} />
          <AvatarTile id="priya"  initial="P" name="Priya Nair"   title="Finance Manager"   active={activeLine?.speaker === "priya"} />
          <AvatarTile id="derek"  initial="D" name="Derek Osei"   title="Data Specialist"   active={activeLine?.speaker === "derek"} />
          {/* You spans bottom-right 2 columns */}
          <div style={{ gridColumn: "2 / 4", background: "#112240", borderRadius: 10, overflow: "hidden", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", position: "relative", border: "1.5px solid transparent" }}>
            <div style={{ fontSize: 32, marginBottom: 8, filter: "drop-shadow(0 2px 8px rgba(0,0,0,0.3))" }}>{userIcon}</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#e0eaf8", marginBottom: 2 }}>{userName}</div>
            <div style={{ fontSize: 10, color: "#7a96b8" }}>Analyst, Office of the President</div>
            <div style={{ position: "absolute", bottom: 8, left: 10, background: "rgba(0,0,0,0.55)", backdropFilter: "blur(4px)", padding: "3px 8px", borderRadius: 5, fontSize: 10.5, fontWeight: 500, color: "white" }}>{userName}</div>
            <div style={{ position: "absolute", top: 8, right: 8, background: "#1a3260", color: "white", fontSize: 9, fontWeight: 700, padding: "2px 7px", borderRadius: 4, letterSpacing: "0.05em", textTransform: "uppercase" as const }}>YOU</div>
            <div style={{ position: "absolute", top: 8, left: 8, background: "rgba(0,0,0,0.5)", width: 22, height: 22, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11 }}>🔇</div>
          </div>
        </div>

        {/* Caption bar */}
        <div style={{ marginTop: 8, background: "rgba(0,0,0,0.45)", backdropFilter: "blur(8px)", borderTop: "1px solid #1e3a5f", borderRadius: "0 0 8px 8px", padding: "10px 14px", display: "flex", alignItems: "flex-start", gap: 10, minHeight: 56 }}>
          {activeLine ? (
            <>
              <span style={{
                fontSize: 10, fontWeight: 700, padding: "2px 9px", borderRadius: 20,
                flexShrink: 0, marginTop: 1, textTransform: "uppercase" as const, letterSpacing: "0.05em",
                background: activeLine.speaker === "jordan" ? "rgba(26,50,96,0.5)" : activeLine.speaker === "priya" ? "rgba(167,139,250,0.25)" : "rgba(14,102,112,0.3)",
                color: activeLine.speaker === "jordan" ? "#93b4e8" : activeLine.speaker === "priya" ? "#c4b5fd" : "#5eead4",
                border: `1px solid ${activeLine.speaker === "jordan" ? "rgba(46,117,182,0.5)" : activeLine.speaker === "priya" ? "rgba(167,139,250,0.4)" : "rgba(20,184,166,0.4)"}`,
              }}>
                {activeLine.name}
              </span>
              <span style={{ fontSize: 12.5, color: "#e0eaf8", lineHeight: 1.6, flex: 1 }}>{activeLine.text}</span>
            </>
          ) : (
            <span style={{ fontSize: 12, color: "#7a96b8", flex: 1 }}>Press play to start the kick-off meeting.</span>
          )}
        </div>

        {/* Progress */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 8, padding: "0 2px" }}>
          <div style={{ flex: 1, height: 3, background: "rgba(255,255,255,0.1)", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", background: "#4ade80", borderRadius: 2, width: `${((current + 1) / LINES.length) * 100}%`, transition: "width 0.4s linear" }} />
          </div>
          <span style={{ fontSize: 11, color: "#7a96b8", minWidth: 40, textAlign: "right" as const, fontFamily: "monospace" }}>
            {Math.max(0, current + 1)} / {LINES.length}
          </span>
        </div>

        {/* Controls */}
        <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 10, marginTop: 10, paddingBottom: 2 }}>
          <button onClick={() => step(-1)} disabled={current <= 0} style={ctrlBtn(false)}>← Prev</button>
          <button onClick={togglePlay} style={ctrlBtn(true)}>{playing ? "⏸ Pause" : "▶ Play"}</button>
          <button onClick={() => step(1)} disabled={current >= LINES.length - 1} style={ctrlBtn(false)}>Next →</button>
        </div>
      </div>

      {/* Continue */}
      {(done || current === LINES.length - 1) && (
        <div style={{ marginTop: 20, textAlign: "center" }}>
          <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 12 }}>
            Meeting complete. Jordan will brief you on your first session with Priya.
          </p>
          <button className="start-btn" onClick={onComplete} style={{ fontSize: 13 }}>
            Continue →
          </button>
        </div>
      )}
    </div>
  );
}

function ctrlBtn(primary: boolean): React.CSSProperties {
  return {
    background: primary ? "#1a3260" : "rgba(255,255,255,0.08)",
    border: primary ? "none" : "1px solid rgba(255,255,255,0.12)",
    borderRadius: 6,
    color: primary ? "#e0eaf8" : "#b0c4e8",
    fontSize: 12,
    fontWeight: 500,
    padding: "7px 18px",
    cursor: "pointer",
    fontFamily: "inherit",
  };
}
