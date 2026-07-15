"use client";
import { useState, useRef } from "react";
import MicButton, { MicState } from "@/components/MicButton";
import VoiceBubble from "@/components/VoiceBubble";

// ── TTS test voices ──────────────────────────────────────────────
const TTS_SAMPLES = [
  { label: "Jordan (Matthew)", voiceId: "Matthew", text: "Alright, let's get into it. The board is asking hard questions and we need answers fast." },
  { label: "Priya (Ruth)",     voiceId: "Ruth",    text: "The operating budget has been in deficit for two consecutive years. Reserves are down to 4.1 million." },
  { label: "Sarah (Joanna)",   voiceId: "Joanna",  text: "Good morning everyone. This sprint we're shipping the customer onboarding flow — let's walk through the requirements." },
];

const SAMPLE_AI_TEXT = "The operating budget has been in deficit for two consecutive years. Reserves are down to 4.1 million. The board's constraint is clear — we need to be back in surplus within two fiscal years.";

export default function TestSpeechPage() {
  // ── TTS state ──
  const [micPreviewState, setMicPreviewState] = useState<MicState>("idle");
  const [aiSpeaking, setAiSpeaking]           = useState(false);
  const [showAIText, setShowAIText]           = useState(false);
  const [ttsLoading, setTtsLoading] = useState<string | null>(null);
  const [ttsError, setTtsError]     = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  async function testTTS(voiceId: string, text: string, label: string) {
    setTtsLoading(label);
    setTtsError(null);
    try {
      const res = await fetch("/api/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, voiceId }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || `HTTP ${res.status}`);
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      if (audioRef.current) {
        audioRef.current.src = url;
        audioRef.current.play();
      }
    } catch (e) {
      setTtsError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setTtsLoading(null);
    }
  }

  // ── STT state ──
  const [sttStatus,     setSttStatus]     = useState<"idle" | "recording" | "processing">("idle");
  const [sttTranscript, setSttTranscript] = useState<string | null>(null);
  const [sttError,      setSttError]      = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);

  async function startRecording() {
    setSttTranscript(null);
    setSttError(null);
    chunksRef.current = [];

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      setSttError(`Mic access denied or unavailable: ${e instanceof Error ? e.message : e}`);
      return;
    }
    const mr = new MediaRecorder(stream);
    mediaRecorderRef.current = mr;
    mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
    mr.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      setSttStatus("processing");
      try {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        const form = new FormData();
        form.append("audio", blob, "recording.webm");
        const res = await fetch("/api/stt", { method: "POST", body: form });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
        setSttTranscript(data.transcript || "(empty transcript)");
      } catch (e) {
        setSttError(e instanceof Error ? e.message : "Unknown error");
      } finally {
        setSttStatus("idle");
      }
    };
    mr.start();
    setSttStatus("recording");
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
  }

  // ── UI ──────────────────────────────────────────────────────────
  const box: React.CSSProperties = {
    background: "var(--surface)", border: "1px solid var(--border)",
    borderRadius: 10, padding: 24, marginBottom: 24,
  };
  const btn: React.CSSProperties = {
    background: "var(--accent)", color: "var(--bg)", border: "none",
    borderRadius: 8, padding: "10px 18px", cursor: "pointer",
    fontFamily: "inherit", fontSize: 13, fontWeight: 600, marginRight: 10,
  };
  const disabledBtn: React.CSSProperties = { ...btn, opacity: 0.4, cursor: "not-allowed" };
  const dangerBtn: React.CSSProperties   = { ...btn, background: "var(--danger)" };

  return (
    <div style={{ maxWidth: 680, margin: "40px auto", padding: "0 24px", fontFamily: "IBM Plex Mono, monospace", color: "var(--text)" }}>
      <h1 style={{ fontFamily: "Space Grotesk, sans-serif", fontSize: 22, marginBottom: 6 }}>
        Speech API Test
      </h1>
      <p style={{ color: "var(--muted)", fontSize: 12, marginBottom: 32 }}>
        Dev-only page. Make sure AWS + Google credentials are in .env.local
      </p>

      {/* ── MicButton preview ── */}
      <div style={box}>
        <h2 style={{ fontSize: 14, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 16 }}>
          Mic Button — UI States
        </h2>
        <div style={{ display: "flex", gap: 40, alignItems: "flex-end", marginBottom: 20 }}>
          {(["idle", "listening"] as MicState[]).map((s) => (
            <div key={s} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10 }}>
              <MicButton state={s} onClick={() => setMicPreviewState(s)} />
              <span style={{ fontSize: 11, color: "var(--muted)", letterSpacing: "0.1em", textTransform: "uppercase" }}>{s}</span>
            </div>
          ))}
        </div>
        <p style={{ fontSize: 12, color: "var(--muted)" }}>
          Live toggle — click a state button above, then try the interactive mic below:
        </p>
        <div style={{ marginTop: 16 }}>
          <div className="voice-input-area" style={{ borderRadius: 10, border: "1px solid var(--border)" }}>
            {micPreviewState !== "idle" && (
              <div className="interim-pill">
                {micPreviewState === "listening" ? "Listening…" : "Transcribing…"}
              </div>
            )}
            <MicButton
              state={micPreviewState}
              onClick={() => setMicPreviewState((s) => s === "idle" ? "listening" : "idle")}
            />
            <button className="mode-toggle" title="Switch to type mode" style={{ position: "absolute", bottom: 16, right: 20 }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <rect x="2" y="6" width="20" height="12" rx="2" />
                <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M8 14h8" />
              </svg>
            </button>
          </div>
        </div>
        <p style={{ fontSize: 11, color: "var(--muted)", marginTop: 10 }}>
          Click the mic to toggle: idle ↔ listening
        </p>
      </div>

      {/* ── AI message preview ── */}
      <div style={box}>
        <h2 style={{ fontSize: 14, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 16 }}>
          AI Message — Voice Mode
        </h2>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 20 }}>
          Toggle speaking / transcript to preview all states.
        </p>

        {/* Simulated AI message row */}
        <div style={{ display: "flex", gap: 12, marginBottom: 16 }}>
          {/* Avatar */}
          <div style={{ width: 32, height: 32, borderRadius: "50%", background: "#2563eb", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 11, fontWeight: 700, color: "#fff", flexShrink: 0, marginTop: 2 }}>P</div>

          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 6 }}>Priya · Finance Manager</div>

            {/* Wave + eye button row */}
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              {aiSpeaking ? (
                <div className="speaking-wave">
                  <span /><span /><span /><span /><span />
                </div>
              ) : (
                <div style={{ display: "flex", alignItems: "center", gap: 2, height: 16 }}>
                  {Array.from({ length: 5 }).map((_, i) => (
                    <span key={i} style={{ display: "block", width: 3, height: 3, borderRadius: "50%", background: "var(--border)" }} />
                  ))}
                </div>
              )}
              <button
                className="show-text-btn"
                onClick={() => setShowAIText(v => !v)}
                style={{ color: showAIText ? "var(--accent)" : undefined }}
              >
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  {showAIText
                    ? <><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/><circle cx="12" cy="12" r="3"/></>
                    : <><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></>
                  }
                </svg>
                {showAIText ? "Hide" : "Show"}
              </button>
            </div>

            {/* Text transcript — revealed on eye click */}
            {showAIText && (
              <div className="msg-bubble ai-bubble" style={{ marginTop: 8, maxWidth: 420 }}>
                {SAMPLE_AI_TEXT}
              </div>
            )}
          </div>
        </div>

        {/* Controls */}
        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          <button style={btn} onClick={() => setAiSpeaking(v => !v)}>
            {aiSpeaking ? "⏹ Stop speaking" : "▶ Simulate speaking"}
          </button>
        </div>
      </div>

      {/* ── Voice bubble preview ── */}
      <div style={box}>
        <h2 style={{ fontSize: 14, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 16 }}>
          Voice Message Bubble
        </h2>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
          How the user's voice message appears in chat (different durations):
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 12, alignItems: "flex-end" }}>
          {[3, 7, 15, 42].map((sec) => (
            <VoiceBubble key={sec} durationSec={sec} />
          ))}
        </div>
      </div>

      {/* ── TTS ── */}
      <div style={box}>
        <h2 style={{ fontSize: 14, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 16 }}>
          TTS — Amazon Polly
        </h2>
        {TTS_SAMPLES.map((s) => (
          <div key={s.label} style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 12, color: "var(--muted)", marginBottom: 6 }}>
              <strong style={{ color: "var(--text)" }}>{s.label}</strong>
              <span style={{ marginLeft: 10, fontStyle: "italic" }}>"{s.text.slice(0, 60)}…"</span>
            </div>
            <button
              style={ttsLoading === s.label ? disabledBtn : btn}
              disabled={!!ttsLoading}
              onClick={() => testTTS(s.voiceId, s.text, s.label)}
            >
              {ttsLoading === s.label ? "Loading…" : "▶ Play"}
            </button>
          </div>
        ))}
        {ttsError && (
          <div style={{ color: "var(--danger)", fontSize: 12, marginTop: 8 }}>
            Error: {ttsError}
          </div>
        )}
        <audio ref={audioRef} style={{ display: "none" }} />
      </div>

      {/* ── STT ── */}
      <div style={box}>
        <h2 style={{ fontSize: 14, letterSpacing: "0.15em", textTransform: "uppercase", color: "var(--muted)", marginBottom: 16 }}>
          STT — Google Chirp
        </h2>
        <p style={{ fontSize: 12, color: "var(--muted)", marginBottom: 16 }}>
          Click record, speak a sentence, then stop.
        </p>

        {sttStatus === "idle" && (
          <button style={btn} onClick={startRecording}>⏺ Start recording</button>
        )}
        {sttStatus === "recording" && (
          <button style={dangerBtn} onClick={stopRecording}>⏹ Stop recording</button>
        )}
        {sttStatus === "processing" && (
          <button style={disabledBtn} disabled>Transcribing…</button>
        )}

        {sttTranscript !== null && (
          <div style={{ marginTop: 16, background: "var(--surface2)", borderRadius: 8, padding: "12px 14px", fontSize: 14, lineHeight: 1.6 }}>
            <span style={{ fontSize: 11, color: "var(--muted)", display: "block", marginBottom: 4 }}>TRANSCRIPT</span>
            {sttTranscript}
          </div>
        )}
        {sttError && (
          <div style={{ color: "var(--danger)", fontSize: 12, marginTop: 12 }}>
            Error: {sttError}
          </div>
        )}
      </div>
    </div>
  );
}
