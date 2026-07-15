"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { STAGES, SCENARIO } from "@/lib/scenarios";
import { callLLM } from "@/lib/llm";
import { Assessment, EvaluationResult, TranscriptEntry, ChatTrialData, TaskSummary } from "@/lib/types";
import { useEvaluation, StageTranscriptData } from "@/lib/useEvaluation";
import Link from "next/link";
import Sidebar from "./Sidebar";
import MessageBubble from "./MessageBubble";
import TypingIndicator from "./TypingIndicator";
import FeedbackOverlay from "./FeedbackOverlay";
import VideoMeeting from "./VideoMeeting";
import ComprehensionCheck from "./ComprehensionCheck";
import ArtifactPanel from "./ArtifactPanel";
import SituationBrief from "./SituationBrief";
import MicButton from "./MicButton";
import VoiceBubble from "./VoiceBubble";
import { useSpeechInput } from "@/hooks/useSpeechInput";
import { useSpeechOutput } from "@/hooks/useSpeechOutput";

interface DisplayMessage {
  id: string;
  type: "user" | "ai" | "system" | "voice";
  sender: string;
  text: string;
  color: string;
  avatar: string;
  durationSec?: number;
}

type StagePhase = "video" | "chat" | "quiz";

// --- Persistence helpers (fire-and-forget) ---

async function apiCreateSession(scenarioId: string): Promise<{ id: string; participantId: string }> {
  const res = await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "createSession", scenarioId }),
  });
  const data = await res.json();
  return data.session;
}

async function apiSaveTranscript(sessionId: string, stageId: string, entries: TranscriptEntry[]) {
  await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "saveTranscript", sessionId, stageId, entries }),
  });
}


interface SimulationProps {
  onComplete?: (trials: ChatTrialData[], summary: TaskSummary) => void;
}

const ICON_OPTIONS = ["🧑‍💻", "👩‍💻", "👨‍💻", "🦊", "🐼", "🦁", "🌟", "🚀", "🎯", "⚡", "🌊", "🔥"];

export default function Simulation({ onComplete }: SimulationProps = {}) {
  const [userProfile, setUserProfile] = useState<{ name: string; icon: string } | null>(null);
  const [profileName, setProfileName] = useState("");
  const [profileIcon, setProfileIcon] = useState("🧑‍💻");
  const [started, setStarted] = useState(false);
  const [currentStage, setCurrentStage] = useState(0);
  const [stagePhase, setStagePhase] = useState<StagePhase>("video");
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [conversationHistory, setConversationHistory] = useState<{ role: string; content: string }[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [stageMessageCount, setStageMessageCount] = useState(0);
  const [inputValue, setInputValue] = useState("");
  const [showNextBar, setShowNextBar] = useState(false);
  const [simulationComplete, setSimulationComplete] = useState(false);
  const [completedStages, setCompletedStages] = useState<Set<number>>(new Set());
  const [visitedStages, setVisitedStages] = useState<Set<number>>(new Set([0]));
  const [showFeedback, setShowFeedback] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [readOnly, setReadOnly] = useState(false);

  // Speech — start with "voice" on both server and first client render to avoid a
  // hydration mismatch, then sync from localStorage after mount.
  const [inputMode, setInputMode] = useState<"voice" | "type">("voice");
  useEffect(() => {
    const saved = localStorage.getItem("inputMode") as "voice" | "type" | null;
    if (saved) setInputMode(saved);
  }, []);
  const [revealedMsgIds, setRevealedMsgIds] = useState<Set<string>>(new Set());
  const [speakingMsgId, setSpeakingMsgId] = useState<string | null>(null);
  const recordingStartRef = useRef<number>(0);
  const sendMessageRef = useRef<((override?: string) => void) | null>(null);

  const currentPollyVoice = SCENARIO.stages[currentStage]?.agentProfile?.pollyVoice ?? "Joanna";
  const speechOutput = useSpeechOutput(currentPollyVoice);
  const speechInput  = useSpeechInput();

  const toggleInputMode = () => {
    const next = inputMode === "voice" ? "type" : "voice";
    setInputMode(next);
    localStorage.setItem("inputMode", next);
  };

  speechInput.onTranscript((t) => sendMessageRef.current?.(t));

  const savedMessagesRef = useRef<Record<number, DisplayMessage[]>>({});
  const savedHistoryRef = useRef<Record<number, { role: string; content: string }[]>>({});
  const allAssessmentsRef = useRef<Assessment[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const msgIdCounter = useRef(0);

  const sessionIdRef = useRef<string | null>(null);
  const stageTranscriptRef = useRef<TranscriptEntry[]>([]);
  const simulationStartRef = useRef<number>(0);

  const nextMsgId = () => `msg-${++msgIdCounter.current}`;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  const addSystemMessage = useCallback((text: string) => {
    setMessages((prev) => [
      ...prev,
      { id: nextMsgId(), type: "system", sender: "System", text, color: "var(--system)", avatar: "S" },
    ]);
  }, []);

  const getAIOpener = useCallback(async (stageIndex: number) => {
    const stage = STAGES[stageIndex];
    setIsLoading(true);
    setIsTyping(true);

    const addOpenerMessage = (text: string) => {
      const id = nextMsgId();
      const now = Date.now();
      setMessages((prev) => [
        ...prev,
        { id, type: "ai", sender: stage.name, text, color: stage.color, avatar: stage.avatar },
      ]);
      setConversationHistory([{ role: "assistant", content: text }]);
      stageTranscriptRef.current.push({ role: "assistant", content: text, timestamp: now, responseTimeMs: null });
      setSpeakingMsgId(id);
      speechOutput.speak(text);
    };

    try {
      const text = await callLLM({
        system: stage.systemPrompt,
        messages: [{ role: "user", content: "[Start the conversation with your opening message.]" }],
      });
      setIsTyping(false);
      addOpenerMessage(text);
    } catch {
      setIsTyping(false);
      const fallbacks = [
        "Alright — any questions before we break?",
        "Hey! So I just finished the prototype — want to walk through it together?",
        "Hey — before you dive in, I want to hear how you're thinking about building this. Walk me through your approach.",
      ];
      addOpenerMessage(fallbacks[stageIndex] ?? "Let's get started.");
    }
    setIsLoading(false);
  }, [speechOutput]);

  const loadStage = useCallback((stageIndex: number) => {
    const stage = STAGES[stageIndex];
    setCurrentStage(stageIndex);
    setVisitedStages(prev => new Set(prev).add(stageIndex));
    setStageMessageCount(0);
    setShowNextBar(false);
    setReadOnly(false);
    setMessages([]);
    setConversationHistory([]);
    stageTranscriptRef.current = [];

    if (stage.stageType === "video-chat") {
      setStagePhase("video");
      // AI opener will be fetched after video completes
    } else {
      setStagePhase("chat");
      addSystemMessage(`Starting conversation with ${stage.name} (${stage.role})`);
      getAIOpener(stageIndex);
    }
  }, [addSystemMessage, getAIOpener]);

  const startSimulation = useCallback(async () => {
    setStarted(true);
    simulationStartRef.current = Date.now();
    try {
      const session = await apiCreateSession(SCENARIO.id);
      sessionIdRef.current = session.id;
    } catch {
      console.warn("Failed to create session — continuing without persistence");
    }
    loadStage(0);
  }, [loadStage]);

  const handleVideoComplete = useCallback(() => {
    setStagePhase("chat");
    addSystemMessage("Sarah opens the floor for questions.");
    getAIOpener(currentStage);
  }, [currentStage, addSystemMessage, getAIOpener]);

  const charLimit = SCENARIO.stages[currentStage]?.turnConfig.maxCharsPerMessage ?? 500;
  const charsRemaining = charLimit - inputValue.length;
  const overLimit = charsRemaining < 0;

  const sendMessage = useCallback(async (override?: string) => {
    const text = (override ?? inputValue).trim();
    if (!text || isLoading || text.length > charLimit) return;

    const stage = STAGES[currentStage];
    const sendTimestamp = Date.now();
    setInputValue("");
    const newCount = stageMessageCount + 1;
    setStageMessageCount(newCount);

    speechOutput.stop();

    const durationSec = inputMode === "voice"
      ? Math.round((Date.now() - recordingStartRef.current) / 1000)
      : undefined;

    setMessages((prev) => [
      ...prev,
      { id: nextMsgId(), type: inputMode === "voice" ? "voice" : "user", sender: userName, text, color: "var(--accent)", avatar: userIcon, durationSec },
    ]);
    stageTranscriptRef.current.push({ role: "user", content: text, timestamp: sendTimestamp, responseTimeMs: null });

    const newHistory = [...conversationHistory, { role: "user", content: text }];
    setConversationHistory(newHistory);

    const stageDefinition = SCENARIO.stages[currentStage];

    // Enforce max turns — after the user's last allowed message, get one final AI reply then lock
    const atMaxTurns = newCount >= stageDefinition.turnConfig.maxTurns;

    setIsLoading(true);
    setIsTyping(true);

    const recentHistory = newHistory.slice(-6);

    try {
      const isLastExchange = atMaxTurns || newCount >= stageDefinition.turnConfig.wrapUpSignalTurn;
      const systemPrompt =
        stage.systemPrompt +
        (atMaxTurns ? " This is the final exchange. Wrap up the conversation naturally with a closing remark." :
         isLastExchange ? " After this message, naturally signal the conversation is wrapping up." : "");

      const reply = await callLLM({ system: systemPrompt, messages: recentHistory });
      const responseTimeMs = Date.now() - sendTimestamp;

      setIsTyping(false);
      const replyId = nextMsgId();
      setMessages((prev) => [
        ...prev,
        { id: replyId, type: "ai", sender: stage.name, text: reply, color: stage.color, avatar: stage.avatar },
      ]);
      setConversationHistory((prev) => [...prev, { role: "assistant", content: reply }]);
      allAssessmentsRef.current.push({ stage: stage.name, userMessage: text, aiReply: reply, responseTimeMs });
      stageTranscriptRef.current.push({ role: "assistant", content: reply, timestamp: Date.now(), responseTimeMs });
      setSpeakingMsgId(replyId);
      speechOutput.speak(reply);

      if (atMaxTurns) {
        setReadOnly(true);
        setShowNextBar(true);
        addSystemMessage("Conversation complete — move on to the next stage.");
      } else if (newCount >= stageDefinition.turnConfig.minTurns) {
        setShowNextBar(true);
      }
    } catch {
      setIsTyping(false);
      const fallbackId = nextMsgId();
      const fallbackText = "Let's continue this shortly.";
      setMessages((prev) => [
        ...prev,
        { id: fallbackId, type: "ai", sender: stage.name, text: fallbackText, color: stage.color, avatar: stage.avatar },
      ]);
      setSpeakingMsgId(fallbackId);
      speechOutput.speak(fallbackText);
      if (atMaxTurns) {
        setReadOnly(true);
        setShowNextBar(true);
        addSystemMessage("Conversation complete — move on to the next stage.");
      } else if (newCount >= stageDefinition.turnConfig.minTurns) {
        setShowNextBar(true);
      }
    }
    setIsLoading(false);
  }, [inputValue, isLoading, currentStage, stageMessageCount, conversationHistory, speechOutput, inputMode]);

  // Keep ref in sync so onTranscript can call it
  sendMessageRef.current = sendMessage;

  const notifyComplete = useCallback((result: EvaluationResult) => {
    if (!onComplete) return;
    const now = Date.now();
    const trials: ChatTrialData[] = STAGES.map((s, i) => ({
      trialIndex: i,
      startedAt: simulationStartRef.current,
      respondedAt: now,
      rt: now - simulationStartRef.current,
      stimulusOnsetAt: simulationStartRef.current,
      taskType: "chat-simulation" as const,
      stageId: s.id,
      stageName: s.name,
      messageCount: allAssessmentsRef.current.filter((a) => a.stage === s.name).length,
      assessmentScores: i === STAGES.length - 1 ? result : undefined,
    }));
    const summary: TaskSummary = {
      totalTrials: STAGES.length,
      completedTrials: STAGES.length,
      meanRT: (now - simulationStartRef.current) / STAGES.length,
    };
    onComplete(trials, summary);
  }, [onComplete]);

  const evaluation = useEvaluation({
    skillDimensions: SCENARIO.assessmentConfig.skillDimensions,
    onComplete: notifyComplete,
  });

  // Save transcript + advance to next stage or trigger evaluation
  const doAdvanceStage = useCallback(() => {
    savedMessagesRef.current[currentStage] = messages;
    savedHistoryRef.current[currentStage] = conversationHistory;
    setCompletedStages(prev => { const n = new Set(prev); n.add(currentStage); return n; });
    if (sessionIdRef.current) {
      apiSaveTranscript(sessionIdRef.current, STAGES[currentStage].id, stageTranscriptRef.current).catch(() => {});
    }
    if (currentStage < STAGES.length - 1) {
      loadStage(currentStage + 1);
    } else {
      setSimulationComplete(true);
      setShowFeedback(true);
      const stageTranscripts: StageTranscriptData[] = SCENARIO.stages.map(s => {
        const entries = allAssessmentsRef.current.filter(a => a.stage === s.agentProfile.name);
        return {
          stageId: s.id,
          badge: s.badge,
          agentName: s.agentProfile.name,
          assessmentRubric: s.agentProfile.assessmentRubric,
          transcript: entries.map(a =>
            `Student: "${a.userMessage}"\nAgent: "${a.aiReply}"`
          ).join("\n"),
        };
      });
      evaluation.trigger(stageTranscripts, {
        sessionId: sessionIdRef.current,
        responseTimesMs: allAssessmentsRef.current.map(a => a.responseTimeMs),
      });
    }
  }, [currentStage, messages, conversationHistory, loadStage, evaluation]);

  const advanceStage = useCallback(() => {
    const stageType = STAGES[currentStage].stageType;
    if (stageType === "video-chat" && stagePhase === "chat") {
      setStagePhase("quiz");
      return;
    }
    doAdvanceStage();
  }, [currentStage, stagePhase, doAdvanceStage]);

  const reviewStage = useCallback((stageIndex: number) => {
    // Save current stage state before leaving
    savedMessagesRef.current[currentStage] = messages;
    savedHistoryRef.current[currentStage] = conversationHistory;

    setShowFeedback(false);
    setCurrentStage(stageIndex);
    setStagePhase("chat");
    setShowNextBar(false);
    stageTranscriptRef.current = [];

    if (simulationComplete) {
      // After Alex finishes — read-only review
      setReadOnly(true);
      const saved = savedMessagesRef.current[stageIndex] ?? [];
      setMessages([
        ...saved,
        { id: nextMsgId(), type: "system", sender: "System", text: "Reviewing past conversation — read only", color: "var(--system)", avatar: "S" },
      ]);
      setConversationHistory(savedHistoryRef.current[stageIndex] ?? []);
      setStageMessageCount(0);
      setShowNextBar(true);
    } else {
      // Mid-simulation — restore conversation and allow chatting
      setReadOnly(false);
      const savedMsgs = savedMessagesRef.current[stageIndex];
      const savedHistory = savedHistoryRef.current[stageIndex];
      if (savedMsgs && savedMsgs.length > 0) {
        setMessages(savedMsgs);
        setConversationHistory(savedHistory ?? []);
        const userCount = savedMsgs.filter((m: DisplayMessage) => m.type === "user").length;
        setStageMessageCount(userCount);
        if (userCount >= SCENARIO.stages[stageIndex].turnConfig.minTurns) setShowNextBar(true);
      } else {
        const stage = STAGES[stageIndex];
        setMessages([]);
        setConversationHistory([]);
        setStageMessageCount(0);
        addSystemMessage(`Starting conversation with ${stage.name} (${stage.role})`);
        getAIOpener(stageIndex);
      }
    }
  }, [currentStage, messages, conversationHistory, simulationComplete, addSystemMessage, getAIOpener]);

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const stage = STAGES[currentStage];
  const stageType = stage.stageType;
  const userName = userProfile?.name ?? "You";
  const userIcon = userProfile?.icon ?? "🧑‍💻";

  // --- Profile setup screen ---
  if (!userProfile) {
    return (
      <div className="start-screen">
        <div className="start-card">
          <div className="start-tag">Before We Begin</div>
          <h1 className="start-title">Who are <em>you?</em></h1>
          <p className="start-desc">We'll use your name and icon to personalize the simulation.</p>

          <div style={{ marginBottom: 24 }}>
            <input
              className="profile-input"
              type="text"
              placeholder="First name"
              value={profileName}
              onChange={(e) => setProfileName(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && profileName.trim()) setUserProfile({ name: profileName.trim(), icon: profileIcon }); }}
              autoFocus
            />
          </div>

          <div style={{ marginBottom: 36 }}>
            <label className="profile-label">Your icon</label>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
              {ICON_OPTIONS.map((icon) => (
                <button
                  key={icon}
                  onClick={() => setProfileIcon(icon)}
                  style={{
                    width: 52, height: 52, borderRadius: 12, fontSize: 26, cursor: "pointer",
                    border: `2px solid ${profileIcon === icon ? "var(--accent)" : "var(--border)"}`,
                    background: profileIcon === icon ? "rgba(240,192,96,0.12)" : "var(--surface2)",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    transition: "border-color 0.15s, background 0.15s",
                  }}
                >
                  {icon}
                </button>
              ))}
            </div>
          </div>

          <button
            className="start-btn"
            disabled={!profileName.trim()}
            onClick={() => setUserProfile({ name: profileName.trim(), icon: profileIcon })}
          >
            Continue →
          </button>
        </div>
      </div>
    );
  }

  // --- Start screen ---
  if (!started) {
    return (
      <div className="start-screen" id="startScreen">
        <div className="start-card">
          <div className="start-tag">Vela SDE Simulation 001</div>
          <h1 className="start-title">
            Build the onboarding module
            <br />
            <em>from scratch.</em>
          </h1>
          <p className="start-desc">{SCENARIO.description}</p>
          <div className="start-stages">
            {STAGES.map((s) => (
              <div key={s.id} className="start-stage">
                <div className="start-stage-dot" style={{ background: s.color }} />
                <span className="start-stage-name">{s.stageTitle}</span>
                <span className="start-stage-desc">{s.desc}</span>
              </div>
            ))}
          </div>
          <button className="start-btn" onClick={startSimulation}>Begin Simulation →</button>
        </div>
      </div>
    );
  }

  // --- Video phase (Stage 1 only) ---
  if (stagePhase === "video") {
    return (
      <>
        <div className="topbar">
          <Link href="/" className="logo" style={{ textDecoration: "none", cursor: "pointer" }}>Think<span>Higher</span></Link>
          <div className="scenario-title">Vela SDE Simulation 001 — Customer Onboarding Sprint</div>
          <StageDots currentStage={currentStage} simulationComplete={simulationComplete} />
        </div>
        <div className="main">
          <Sidebar currentStage={currentStage} simulationComplete={simulationComplete} completedStages={completedStages} visitedStages={visitedStages} onReviewStage={reviewStage} />
          <div className="video-meeting-area">
            {stage.situationBrief && <SituationBrief data={stage.situationBrief} userProfile={userProfile ?? undefined} />}
            <div className="video-meeting-frame">
              <VideoMeeting onComplete={handleVideoComplete} userName={userName} userIcon={userIcon} />
            </div>
          </div>
        </div>
      </>
    );
  }

  // --- Quiz phase (Stage 1 only) ---
  if (stagePhase === "quiz") {
    const questions = stage.comprehensionQuestions ?? [];
    return (
      <>
        <div className="topbar">
          <Link href="/" className="logo" style={{ textDecoration: "none", cursor: "pointer" }}>Think<span>Higher</span></Link>
          <div className="scenario-title">Vela SDE Simulation 001 — Customer Onboarding Sprint</div>
          <StageDots currentStage={currentStage} simulationComplete={simulationComplete} />
        </div>
        <div className="main">
          <Sidebar currentStage={currentStage} simulationComplete={simulationComplete} completedStages={completedStages} visitedStages={visitedStages} onReviewStage={reviewStage} />
          <div className="comprehension-area">
            {stage.situationBrief && <SituationBrief key={`${currentStage}-quiz`} data={stage.situationBrief} defaultCollapsed userProfile={userProfile ?? undefined} />}
            <div style={{ marginTop: 16, width: "100%", maxWidth: 600 }}>
              <ComprehensionCheck questions={questions} onComplete={doAdvanceStage} />
            </div>
          </div>
        </div>
      </>
    );
  }

  // --- Chat (and chat-artifact) phase ---
  const hasArtifact = stageType === "chat-artifact" && !!stage.artifactSrc;
  const isQuizPending = stageType === "video-chat" && stagePhase === "chat";

  return (
    <>
      <div className="topbar">
        <div className="logo">Think<span>Higher</span></div>
        <div className="scenario-title">Vela SDE Simulation 001 — Customer Onboarding Sprint</div>
        <StageDots currentStage={currentStage} simulationComplete={simulationComplete} />
      </div>

      <div className="main">
        <Sidebar currentStage={currentStage} simulationComplete={simulationComplete} completedStages={completedStages} visitedStages={visitedStages} onReviewStage={reviewStage} />

        <div className="chat-area">
          {stage.situationBrief && <SituationBrief key={`${currentStage}-${stagePhase}`} data={stage.situationBrief} defaultCollapsed userProfile={userProfile ?? undefined} />}
          <div className="stage-header">
            <div className="stage-badge" style={{ background: `${stage.color}22`, color: stage.color, border: `1px solid ${stage.color}44` }}>
              {stage.badge}{readOnly ? " · Review" : ""}
            </div>
            <div className="stage-desc">{stage.desc}</div>
          </div>

          <div className="messages">
            {messages.map((msg) => {
              if (msg.type === "system") return (
                <div key={msg.id} style={{ display: "flex", justifyContent: "center", margin: "4px 0" }}>
                  <div className="system-bubble">{msg.text}</div>
                </div>
              );
              if (msg.type === "voice") return (
                <div key={msg.id} className="message user-msg">
                  <div className="msg-avatar" style={{ background: "var(--surface2)", fontSize: 16 }}>{msg.avatar}</div>
                  <div className="msg-content">
                    <div className="msg-sender" style={{ textAlign: "right" }}>{msg.sender}</div>
                    <VoiceBubble durationSec={msg.durationSec ?? 0} />
                  </div>
                </div>
              );
              if (msg.type === "ai") {
                const isThisSpeaking = speakingMsgId === msg.id && speechOutput.isSpeaking;
                const isRevealed = revealedMsgIds.has(msg.id);
                const toggleReveal = () => setRevealedMsgIds(prev => {
                  const next = new Set(prev);
                  next.has(msg.id) ? next.delete(msg.id) : next.add(msg.id);
                  return next;
                });
                return (
                  <div key={msg.id} className="message">
                    <div className="msg-avatar" style={{ background: msg.color + "33", color: msg.color, fontSize: 13, fontWeight: 700 }}>{msg.avatar}</div>
                    <div className="msg-content">
                      <div className="msg-sender">{msg.sender}</div>
                      <div style={{ display: "flex", alignItems: "center", gap: 10, minHeight: 28 }}>
                        {isThisSpeaking ? (
                          <div className="speaking-wave"><span /><span /><span /><span /><span /></div>
                        ) : (
                          <div style={{ display: "flex", gap: 3, alignItems: "center" }}>
                            {[0,1,2,3,4].map(i => <span key={i} style={{ display:"block", width:3, height:3, borderRadius:"50%", background:"var(--border)" }} />)}
                          </div>
                        )}
                        {inputMode === "voice" && (
                          <button className="show-text-btn" onClick={toggleReveal}
                            disabled={isThisSpeaking}
                            style={{ color: isRevealed ? "var(--accent)" : undefined, opacity: isThisSpeaking ? 0.35 : 1, cursor: isThisSpeaking ? "default" : "pointer" }}>
                            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                              {isRevealed
                                ? <><path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7"/><circle cx="12" cy="12" r="3"/></>
                                : <><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94"/><path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19"/><line x1="1" y1="1" x2="23" y2="23"/></>
                              }
                            </svg>
                            {isRevealed ? "Hide" : "Show"}
                          </button>
                        )}
                      </div>
                      {(inputMode === "type" || isRevealed) && (
                        <div className="msg-bubble ai-bubble" style={{ marginTop: 6 }}>{msg.text}</div>
                      )}
                    </div>
                  </div>
                );
              }
              return (
                <MessageBubble key={msg.id} sender={msg.sender} text={msg.text}
                  color={msg.color} avatarLetter={msg.avatar} isUser={true} />
              );
            })}
            {isTyping && <TypingIndicator color={stage.color} avatar={stage.avatar} name={stage.name} />}
            <div ref={messagesEndRef} />
          </div>

          {showNextBar && (
            <div className="next-stage-bar visible">
              <div className="next-stage-hint">
                {simulationComplete && readOnly ? (
                  <span><em>Read-only review mode.</em> Click any stage in the sidebar to switch.</span>
                ) : stageMessageCount >= SCENARIO.stages[currentStage].turnConfig.wrapUpSignalTurn ? (
                  <span><em>Conversation is wrapping up.</em> Continue or move on when ready.</span>
                ) : (
                  "Feel free to keep the conversation going, or move on when ready."
                )}
              </div>
              {simulationComplete && readOnly ? (
                <button className="next-stage-btn finish-btn" onClick={() => setShowFeedback(true)}>View Feedback</button>
              ) : isQuizPending ? (
                <button className="next-stage-btn" onClick={advanceStage}>Continue to Quiz →</button>
              ) : currentStage < STAGES.length - 1 ? (
                <button className="next-stage-btn" onClick={advanceStage}>Next Stage →</button>
              ) : (
                <button className="next-stage-btn finish-btn" onClick={advanceStage}>Finish & See Feedback</button>
              )}
            </div>
          )}

          {inputMode === "voice" ? (
            <div className="voice-input-area">
              {speechInput.interimText && (
                <div className="interim-pill">{speechInput.interimText}</div>
              )}
              <MicButton
                state={speechInput.state}
                onClick={() => {
                  if (speechInput.state === "idle") {
                    recordingStartRef.current = Date.now();
                    speechInput.start();
                  } else {
                    speechInput.stop();
                  }
                }}
                disabled={isLoading || readOnly}
              />
              <button className="mode-toggle" onClick={toggleInputMode} title="Switch to typing" aria-label="Switch to typing">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="2" y="6" width="20" height="12" rx="2"/>
                  <path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M8 14h8"/>
                </svg>
              </button>
            </div>
          ) : (
            <div className="input-area">
              <div className="input-row">
                <textarea
                  ref={inputRef}
                  className="input-box"
                  placeholder={readOnly ? "Read-only — simulation complete" : "Type your response..."}
                  rows={1}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKey}
                  disabled={isLoading || readOnly}
                  onInput={(e) => {
                    const el = e.target as HTMLTextAreaElement;
                    el.style.height = "auto";
                    el.style.height = Math.min(el.scrollHeight, 120) + "px";
                  }}
                />
                <button className="send-btn" onClick={() => sendMessage()} disabled={isLoading || readOnly || overLimit}>Send →</button>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div className="input-hint">This is a simulation. Respond as you would in a real workplace.</div>
                {!readOnly && inputValue.length > charLimit * 0.8 && (
                  <div style={{ fontSize: "10px", fontFamily: "'IBM Plex Mono', monospace", color: overLimit ? "#e55" : "var(--muted)", whiteSpace: "nowrap", marginLeft: 8 }}>
                    {charsRemaining}
                  </div>
                )}
              </div>
              <button className="mode-toggle" onClick={toggleInputMode} title="Switch to voice" aria-label="Switch to voice"
                style={{ position: "static", marginTop: 8 }}>
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <rect x="9" y="2" width="6" height="12" rx="3"/>
                  <path d="M5 10a7 7 0 0 0 14 0"/>
                  <line x1="12" y1="20" x2="12" y2="23"/>
                  <line x1="9" y1="23" x2="15" y2="23"/>
                </svg>
              </button>
            </div>
          )}
        </div>

        {hasArtifact && (
          <ArtifactPanel src={stage.artifactSrc!} title="Vela Onboarding Prototype" />
        )}
      </div>

      <FeedbackOverlay
        visible={showFeedback}
        result={evaluation.result}
        dimensions={SCENARIO.assessmentConfig.skillDimensions}
        subtitle={`${SCENARIO.title} · Scenario ${SCENARIO.id}`}
        onClose={() => {
          setShowFeedback(false);
          if (simulationComplete) reviewStage(currentStage);
        }}
      />
    </>
  );
}

// Extracted to avoid repeating in all render branches
function StageDots({ currentStage, simulationComplete }: { currentStage: number; simulationComplete: boolean }) {
  return (
    <div className="stage-indicators">
      {STAGES.map((_, i) => {
        const classes = [
          "stage-dot",
          i < currentStage || simulationComplete ? "done" : "",
          i === currentStage ? "active" : "",
        ].filter(Boolean).join(" ");
        return <div key={i} className={classes} data-stage={i} />;
      })}
    </div>
  );
}
