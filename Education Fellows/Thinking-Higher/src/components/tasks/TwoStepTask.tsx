"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { TwoStepTrialData, TaskSummary } from "@/lib/types";

interface TwoStepTaskProps {
  numTrials?: number;
  onComplete: (trials: TwoStepTrialData[], summary: TaskSummary) => void;
}

type TaskPhase =
  | "instructions"
  | "stage1"
  | "transition"
  | "stage2"
  | "feedback"
  | "complete";

// Gaussian random via Box-Muller
function gaussianRandom(): number {
  let u = 0,
    v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}

function clamp(val: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, val));
}

export default function TwoStepTask({
  numTrials = 200,
  onComplete,
}: TwoStepTaskProps) {
  // Reward probabilities: [stateX_option0, stateX_option1, stateY_option0, stateY_option1]
  const rewardProbsRef = useRef<number[]>([]);
  const trialsRef = useRef<TwoStepTrialData[]>([]);
  const trialIndexRef = useRef(0);

  // Per-trial transient state
  const [phase, setPhase] = useState<TaskPhase>("instructions");
  const [stage1Choice, setStage1Choice] = useState<0 | 1 | null>(null);
  const [stage2State, setStage2State] = useState<0 | 1 | null>(null);
  const [stage2Choice, setStage2Choice] = useState<0 | 1 | null>(null);
  const [transitionType, setTransitionType] = useState<"common" | "rare">(
    "common"
  );
  const [reward, setReward] = useState<0 | 1>(0);
  const [trialCount, setTrialCount] = useState(0);

  // Timing refs
  const trialStartRef = useRef(0);
  const stage1OnsetRef = useRef(0);
  const stage2OnsetRef = useRef(0);
  const stage1RTRef = useRef(0);

  // Highlighted selection for visual feedback before transition
  const [stage1Highlighted, setStage1Highlighted] = useState<0 | 1 | null>(
    null
  );
  const [stage2Highlighted, setStage2Highlighted] = useState<0 | 1 | null>(
    null
  );

  // Initialize reward probabilities
  useEffect(() => {
    if (rewardProbsRef.current.length === 0) {
      rewardProbsRef.current = Array.from(
        { length: 4 },
        () => 0.3 + Math.random() * 0.4
      );
    }
  }, []);

  // Drift reward probabilities (called after each trial)
  const driftRewardProbs = useCallback(() => {
    rewardProbsRef.current = rewardProbsRef.current.map((p) =>
      clamp(p + gaussianRandom() * 0.025, 0.25, 0.75)
    );
  }, []);

  // Start a new trial
  const startTrial = useCallback(() => {
    const now = performance.now();
    trialStartRef.current = now;
    setStage1Choice(null);
    setStage2State(null);
    setStage2Choice(null);
    setStage1Highlighted(null);
    setStage2Highlighted(null);
    setReward(0);
    setPhase("stage1");
    // Use rAF to record accurate stimulus onset
    requestAnimationFrame(() => {
      stage1OnsetRef.current = performance.now();
    });
  }, []);

  // Handle stage 1 choice
  const handleStage1Choice = useCallback(
    (choice: 0 | 1) => {
      if (phase !== "stage1") return;
      const now = performance.now();
      const rt = now - stage1OnsetRef.current;
      stage1RTRef.current = rt;
      setStage1Choice(choice);
      setStage1Highlighted(choice);

      // Determine transition: choice 0 -> state 0 (70%) / state 1 (30%)
      //                        choice 1 -> state 1 (70%) / state 0 (30%)
      const isCommon = Math.random() < 0.7;
      const reachedState: 0 | 1 = isCommon
        ? choice
        : choice === 0
          ? 1
          : 0;
      setStage2State(reachedState);
      setTransitionType(isCommon ? "common" : "rare");

      // Transition animation phase
      setPhase("transition");
      setTimeout(() => {
        setPhase("stage2");
        requestAnimationFrame(() => {
          stage2OnsetRef.current = performance.now();
        });
      }, 500);
    },
    [phase]
  );

  // Handle stage 2 choice
  const handleStage2Choice = useCallback(
    (choice: 0 | 1) => {
      if (phase !== "stage2" || stage2State === null || stage1Choice === null)
        return;
      const now = performance.now();
      const stage2RT = now - stage2OnsetRef.current;
      setStage2Choice(choice);
      setStage2Highlighted(choice);

      // Determine reward based on reward probability
      const probIndex = stage2State * 2 + choice;
      const rewardProb = rewardProbsRef.current[probIndex];
      const gotReward: 0 | 1 = Math.random() < rewardProb ? 1 : 0;
      setReward(gotReward);

      // Record trial data
      const trialData: TwoStepTrialData = {
        taskType: "two-step",
        trialIndex: trialIndexRef.current,
        startedAt: trialStartRef.current,
        respondedAt: now,
        rt: stage1RTRef.current + stage2RT,
        stimulusOnsetAt: stage1OnsetRef.current,
        stage1Choice: stage1Choice,
        stage2State: stage2State,
        stage2Choice: choice,
        transitionType: transitionType,
        reward: gotReward,
        rewardProbabilities: [...rewardProbsRef.current],
        stage1RT: stage1RTRef.current,
        stage2RT: stage2RT,
      };
      trialsRef.current.push(trialData);

      // Drift reward probabilities for next trial
      driftRewardProbs();

      // Show feedback
      setPhase("feedback");
      setTimeout(() => {
        trialIndexRef.current += 1;
        setTrialCount(trialIndexRef.current);
        if (trialIndexRef.current >= numTrials) {
          setPhase("complete");
        } else {
          startTrial();
        }
      }, 1000);
    },
    [
      phase,
      stage2State,
      stage1Choice,
      transitionType,
      driftRewardProbs,
      numTrials,
      startTrial,
    ]
  );

  // Keyboard handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (phase === "stage1") {
        if (e.key === "1" || e.key === "ArrowLeft") handleStage1Choice(0);
        if (e.key === "2" || e.key === "ArrowRight") handleStage1Choice(1);
      } else if (phase === "stage2") {
        if (e.key === "1" || e.key === "ArrowLeft") handleStage2Choice(0);
        if (e.key === "2" || e.key === "ArrowRight") handleStage2Choice(1);
      } else if (phase === "instructions") {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          startTrial();
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [phase, handleStage1Choice, handleStage2Choice, startTrial]);

  // Compute summary and call onComplete when done
  useEffect(() => {
    if (phase !== "complete") return;
    const trials = trialsRef.current;
    const totalReward = trials.reduce((sum, t) => sum + t.reward, 0);
    const meanRT =
      trials.reduce((sum, t) => sum + t.rt, 0) / trials.length;

    // Compute stay probabilities for model-based / model-free analysis
    let commonRewarded = 0,
      commonRewardedStay = 0;
    let commonUnrewarded = 0,
      commonUnrewardedStay = 0;
    let rareRewarded = 0,
      rareRewardedStay = 0;
    let rareUnrewarded = 0,
      rareUnrewardedStay = 0;

    for (let i = 0; i < trials.length - 1; i++) {
      const curr = trials[i];
      const next = trials[i + 1];
      const stayed = curr.stage1Choice === next.stage1Choice;

      if (curr.transitionType === "common") {
        if (curr.reward === 1) {
          commonRewarded++;
          if (stayed) commonRewardedStay++;
        } else {
          commonUnrewarded++;
          if (stayed) commonUnrewardedStay++;
        }
      } else {
        if (curr.reward === 1) {
          rareRewarded++;
          if (stayed) rareRewardedStay++;
        } else {
          rareUnrewarded++;
          if (stayed) rareUnrewardedStay++;
        }
      }
    }

    const stayCommonRewarded =
      commonRewarded > 0 ? commonRewardedStay / commonRewarded : 0;
    const stayCommonUnrewarded =
      commonUnrewarded > 0 ? commonUnrewardedStay / commonUnrewarded : 0;
    const stayRareRewarded =
      rareRewarded > 0 ? rareRewardedStay / rareRewarded : 0;
    const stayRareUnrewarded =
      rareUnrewarded > 0 ? rareUnrewardedStay / rareUnrewarded : 0;

    const modelBasedIndex = stayRareRewarded - stayRareUnrewarded;

    const summary: TaskSummary = {
      totalTrials: trials.length,
      completedTrials: trials.length,
      meanRT: Math.round(meanRT),
      totalReward,
      stayCommonRewarded,
      stayCommonUnrewarded,
      stayRareRewarded,
      stayRareUnrewarded,
      modelBasedIndex,
    };

    onComplete(trials, summary);
  }, [phase, onComplete]);

  // --- Styles ---
  const containerStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100%",
    padding: "24px",
    fontFamily: "'IBM Plex Mono', monospace",
    color: "var(--text)",
    background: "var(--bg)",
    position: "relative",
  };

  const progressStyle: React.CSSProperties = {
    position: "absolute",
    top: "16px",
    right: "24px",
    fontSize: "11px",
    color: "var(--muted)",
    letterSpacing: "0.05em",
  };

  const stageLabelStyle: React.CSSProperties = {
    fontSize: "10px",
    letterSpacing: "0.2em",
    textTransform: "uppercase",
    color: "var(--muted)",
    marginBottom: "20px",
  };

  const buttonBase: React.CSSProperties = {
    border: "2px solid var(--border)",
    borderRadius: "16px",
    padding: "24px 32px",
    cursor: "pointer",
    transition: "all 0.15s ease",
    fontFamily: "'Syne', sans-serif",
    fontSize: "14px",
    fontWeight: 600,
    background: "var(--surface)",
    color: "var(--text)",
    minWidth: "160px",
    textAlign: "center",
  };

  const rocketButtonStyle = (
    side: 0 | 1,
    highlighted: boolean
  ): React.CSSProperties => ({
    ...buttonBase,
    borderColor: highlighted
      ? side === 0
        ? "var(--accent)"
        : "var(--accent2)"
      : "var(--border)",
    background: highlighted
      ? side === 0
        ? "rgba(240, 192, 96, 0.15)"
        : "rgba(96, 168, 240, 0.15)"
      : "var(--surface)",
    boxShadow: highlighted
      ? side === 0
        ? "0 0 20px rgba(240, 192, 96, 0.3)"
        : "0 0 20px rgba(96, 168, 240, 0.3)"
      : "none",
    transform: highlighted ? "scale(1.05)" : "scale(1)",
  });

  const planetColors = {
    0: { bg: "rgba(96, 168, 240, 0.1)", border: "var(--accent2)", text: "var(--accent2)" },
    1: { bg: "rgba(200, 144, 240, 0.1)", border: "#c890f0", text: "#c890f0" },
  };

  const artifactButtonStyle = (
    state: 0 | 1,
    highlighted: boolean
  ): React.CSSProperties => {
    const colors = planetColors[state];
    return {
      ...buttonBase,
      borderColor: highlighted ? colors.border : "var(--border)",
      background: highlighted ? colors.bg : "var(--surface)",
      boxShadow: highlighted ? `0 0 20px ${colors.border}44` : "none",
      transform: highlighted ? "scale(1.05)" : "scale(1)",
    };
  };

  // --- Render ---

  if (phase === "instructions") {
    return (
      <div style={containerStyle}>
        <div
          style={{
            maxWidth: "560px",
            width: "100%",
          }}
        >
          <div
            style={{
              fontSize: "10px",
              letterSpacing: "0.2em",
              textTransform: "uppercase",
              color: "var(--accent)",
              marginBottom: "16px",
            }}
          >
            Two-Step Task
          </div>
          <h2
            style={{
              fontFamily: "'Syne', sans-serif",
              fontSize: "24px",
              fontWeight: 700,
              marginBottom: "16px",
              color: "var(--text)",
            }}
          >
            Rockets & Planets
          </h2>
          <div
            style={{
              fontSize: "12.5px",
              lineHeight: "1.75",
              color: "var(--muted)",
              marginBottom: "24px",
              whiteSpace: "pre-line",
            }}
          >
            {`In this task, you'll make two choices per trial.

First, choose one of two rockets. Each rocket usually takes you to a specific planet, but sometimes you end up at the other planet.

Once you arrive, choose one of two options on that planet. Each option has a chance of giving a reward, but these chances slowly change over time.

Your goal: earn as many rewards as possible over ${numTrials} trials.`}
          </div>
          <div
            style={{
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              marginBottom: "24px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "10px 14px",
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                fontSize: "11px",
              }}
            >
              <span style={{ fontSize: "18px" }}>1 / &#8592;</span>
              <span style={{ color: "var(--muted)" }}>Select left option</span>
            </div>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "12px",
                padding: "10px 14px",
                background: "var(--surface)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
                fontSize: "11px",
              }}
            >
              <span style={{ fontSize: "18px" }}>2 / &#8594;</span>
              <span style={{ color: "var(--muted)" }}>Select right option</span>
            </div>
          </div>
          <button
            onClick={startTrial}
            style={{
              background: "var(--accent)",
              color: "var(--bg)",
              border: "none",
              borderRadius: "10px",
              padding: "14px 28px",
              fontFamily: "'Syne', sans-serif",
              fontSize: "13px",
              fontWeight: 700,
              cursor: "pointer",
              letterSpacing: "0.05em",
              transition: "opacity 0.2s",
            }}
          >
            Start Task
          </button>
        </div>
      </div>
    );
  }

  if (phase === "complete") {
    return (
      <div style={containerStyle}>
        <div
          style={{
            fontSize: "10px",
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            color: "var(--success)",
            marginBottom: "12px",
          }}
        >
          Task Complete
        </div>
        <div
          style={{
            fontFamily: "'Syne', sans-serif",
            fontSize: "20px",
            fontWeight: 700,
            color: "var(--text)",
            marginBottom: "8px",
          }}
        >
          Processing results...
        </div>
        <div style={{ fontSize: "12px", color: "var(--muted)" }}>
          {numTrials} trials completed
        </div>
      </div>
    );
  }

  return (
    <div style={containerStyle}>
      {/* Progress */}
      <div style={progressStyle}>
        Trial {trialCount + 1} / {numTrials}
      </div>

      {/* Stage 1 */}
      {phase === "stage1" && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "16px",
          }}
        >
          <div style={stageLabelStyle}>Stage 1 — Choose a Rocket</div>
          <div style={{ display: "flex", gap: "40px" }}>
            <button
              onClick={() => handleStage1Choice(0)}
              style={rocketButtonStyle(0, stage1Highlighted === 0)}
              onMouseEnter={(e) => {
                if (stage1Highlighted === null) {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    "var(--accent)";
                  (e.currentTarget as HTMLElement).style.background =
                    "rgba(240, 192, 96, 0.08)";
                }
              }}
              onMouseLeave={(e) => {
                if (stage1Highlighted === null) {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    "var(--border)";
                  (e.currentTarget as HTMLElement).style.background =
                    "var(--surface)";
                }
              }}
            >
              <div style={{ fontSize: "36px", marginBottom: "8px" }}>
                &#x1F680;
              </div>
              <div style={{ color: "var(--accent)", fontSize: "12px" }}>
                Rocket A
              </div>
              <div
                style={{
                  fontSize: "9px",
                  color: "var(--muted)",
                  marginTop: "4px",
                }}
              >
                Press 1 or &#8592;
              </div>
            </button>
            <button
              onClick={() => handleStage1Choice(1)}
              style={rocketButtonStyle(1, stage1Highlighted === 1)}
              onMouseEnter={(e) => {
                if (stage1Highlighted === null) {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    "var(--accent2)";
                  (e.currentTarget as HTMLElement).style.background =
                    "rgba(96, 168, 240, 0.08)";
                }
              }}
              onMouseLeave={(e) => {
                if (stage1Highlighted === null) {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    "var(--border)";
                  (e.currentTarget as HTMLElement).style.background =
                    "var(--surface)";
                }
              }}
            >
              <div style={{ fontSize: "36px", marginBottom: "8px" }}>
                &#x1F680;
              </div>
              <div style={{ color: "var(--accent2)", fontSize: "12px" }}>
                Rocket B
              </div>
              <div
                style={{
                  fontSize: "9px",
                  color: "var(--muted)",
                  marginTop: "4px",
                }}
              >
                Press 2 or &#8594;
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Transition */}
      {phase === "transition" && stage2State !== null && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "12px",
            animation: "fadeUp 0.3s ease forwards",
          }}
        >
          <div
            style={{
              fontSize: "10px",
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              color: "var(--muted)",
            }}
          >
            {transitionType === "common" ? "Common" : "Rare"} Transition
          </div>
          <div style={{ fontSize: "48px" }}>
            {stage2State === 0 ? "\u{1FA90}" : "\u{1F52E}"}
          </div>
          <div
            style={{
              fontFamily: "'Syne', sans-serif",
              fontSize: "18px",
              fontWeight: 700,
              color: planetColors[stage2State].text,
            }}
          >
            {stage2State === 0 ? "Planet Alpha" : "Planet Beta"}
          </div>
          <div
            style={{
              fontSize: "11px",
              color: "var(--muted)",
              fontStyle: "italic",
            }}
          >
            Arriving...
          </div>
        </div>
      )}

      {/* Stage 2 */}
      {phase === "stage2" && stage2State !== null && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "16px",
          }}
        >
          <div style={stageLabelStyle}>
            Stage 2 —{" "}
            <span style={{ color: planetColors[stage2State].text }}>
              {stage2State === 0 ? "Planet Alpha" : "Planet Beta"}
            </span>
          </div>
          <div style={{ display: "flex", gap: "40px" }}>
            <button
              onClick={() => handleStage2Choice(0)}
              style={artifactButtonStyle(
                stage2State,
                stage2Highlighted === 0
              )}
              onMouseEnter={(e) => {
                if (stage2Highlighted === null) {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    planetColors[stage2State].border;
                  (e.currentTarget as HTMLElement).style.background =
                    planetColors[stage2State].bg;
                }
              }}
              onMouseLeave={(e) => {
                if (stage2Highlighted === null) {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    "var(--border)";
                  (e.currentTarget as HTMLElement).style.background =
                    "var(--surface)";
                }
              }}
            >
              <div style={{ fontSize: "36px", marginBottom: "8px" }}>
                {stage2State === 0 ? "\u{1F48E}" : "\u{1F319}"}
              </div>
              <div
                style={{
                  color: planetColors[stage2State].text,
                  fontSize: "12px",
                }}
              >
                {stage2State === 0 ? "Crystal" : "Moonstone"}
              </div>
              <div
                style={{
                  fontSize: "9px",
                  color: "var(--muted)",
                  marginTop: "4px",
                }}
              >
                Press 1 or &#8592;
              </div>
            </button>
            <button
              onClick={() => handleStage2Choice(1)}
              style={artifactButtonStyle(
                stage2State,
                stage2Highlighted === 1
              )}
              onMouseEnter={(e) => {
                if (stage2Highlighted === null) {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    planetColors[stage2State].border;
                  (e.currentTarget as HTMLElement).style.background =
                    planetColors[stage2State].bg;
                }
              }}
              onMouseLeave={(e) => {
                if (stage2Highlighted === null) {
                  (e.currentTarget as HTMLElement).style.borderColor =
                    "var(--border)";
                  (e.currentTarget as HTMLElement).style.background =
                    "var(--surface)";
                }
              }}
            >
              <div style={{ fontSize: "36px", marginBottom: "8px" }}>
                {stage2State === 0 ? "\u{2B50}" : "\u{1F30A}"}
              </div>
              <div
                style={{
                  color: planetColors[stage2State].text,
                  fontSize: "12px",
                }}
              >
                {stage2State === 0 ? "Star Shard" : "Tidestone"}
              </div>
              <div
                style={{
                  fontSize: "9px",
                  color: "var(--muted)",
                  marginTop: "4px",
                }}
              >
                Press 2 or &#8594;
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Feedback */}
      {phase === "feedback" && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "12px",
            animation: "fadeUp 0.3s ease forwards",
          }}
        >
          <div
            style={{
              fontSize: reward === 1 ? "64px" : "48px",
              transition: "font-size 0.2s",
            }}
          >
            {reward === 1 ? "\u{1F4B0}" : "\u{274C}"}
          </div>
          <div
            style={{
              fontFamily: "'Syne', sans-serif",
              fontSize: "28px",
              fontWeight: 700,
              color: reward === 1 ? "var(--success)" : "var(--muted)",
            }}
          >
            {reward === 1 ? "+1" : "0"}
          </div>
          <div style={{ fontSize: "11px", color: "var(--muted)" }}>
            {reward === 1 ? "Reward collected!" : "No reward this time."}
          </div>
        </div>
      )}

      {/* Total reward display */}
      <div
          style={{
            position: "absolute",
            top: "16px",
            left: "24px",
            fontSize: "11px",
            color: "var(--muted)",
            letterSpacing: "0.05em",
          }}
        >
          Total:{" "}
          <span style={{ color: "var(--success)", fontWeight: 600 }}>
            {trialsRef.current.reduce((s, t) => s + t.reward, 0)}
          </span>
        </div>
    </div>
  );
}
