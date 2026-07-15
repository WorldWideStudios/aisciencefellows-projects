"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import type { ReversalTrialData, TaskSummary } from "@/lib/types";

interface ReversalLearningProps {
  numTrials?: number;
  reversalTrial?: number;
  onComplete: (trials: ReversalTrialData[], summary: TaskSummary) => void;
}

type Phase = "fixation" | "choose" | "feedback" | "done";

const PRE_REVERSAL_PROBS: [number, number, number] = [0.7, 0.2, 0.1];
const POST_REVERSAL_PROBS: [number, number, number] = [0.1, 0.2, 0.7];

export default function ReversalLearning({
  numTrials = 120,
  reversalTrial = 60,
  onComplete,
}: ReversalLearningProps) {
  const [phase, setPhase] = useState<Phase>("fixation");
  const [trialIndex, setTrialIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [lastReward, setLastReward] = useState<0 | 1 | null>(null);
  const [lastChosen, setLastChosen] = useState<0 | 1 | 2 | null>(null);
  const [qValues, setQValues] = useState<[number, number, number]>([0.33, 0.33, 0.33]);

  const trialsRef = useRef<ReversalTrialData[]>([]);
  const qRef = useRef<[number, number, number]>([0.33, 0.33, 0.33]);
  const trialStartRef = useRef(0);
  const stimulusOnsetRef = useRef(0);
  const phaseRef = useRef<Phase>("fixation");
  const trialIndexRef = useRef(0);

  // Keep refs in sync with state
  phaseRef.current = phase;
  trialIndexRef.current = trialIndex;

  const getCurrentProbs = useCallback(
    (idx: number): [number, number, number] => {
      return idx < reversalTrial ? PRE_REVERSAL_PROBS : POST_REVERSAL_PROBS;
    },
    [reversalTrial]
  );

  const getPhaseLabel = useCallback(
    (idx: number): "pre-reversal" | "post-reversal" => {
      return idx < reversalTrial ? "pre-reversal" : "post-reversal";
    },
    [reversalTrial]
  );

  const getTrialInPhase = useCallback(
    (idx: number): number => {
      return idx < reversalTrial ? idx : idx - reversalTrial;
    },
    [reversalTrial]
  );

  const startChoosePhase = useCallback(() => {
    requestAnimationFrame(() => {
      stimulusOnsetRef.current = performance.now();
      setPhase("choose");
    });
  }, []);

  // Start first fixation on mount
  useEffect(() => {
    trialStartRef.current = performance.now();
    const timer = setTimeout(startChoosePhase, 500);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const computeSummary = useCallback((): TaskSummary => {
    const trials = trialsRef.current;
    const rts = trials.map((t) => t.rt);
    const meanRT = rts.reduce((a, b) => a + b, 0) / rts.length;
    const totalReward = trials.reduce((a, t) => a + t.reward, 0);

    // Pre-reversal accuracy: % choosing arm 0 (best) in trials 41-60 (indices 40-59)
    const latePreTrials = trials.filter(
      (t) => t.trialIndex >= 40 && t.trialIndex < reversalTrial
    );
    const preReversalAccuracy =
      latePreTrials.length > 0
        ? latePreTrials.filter((t) => t.chosenArm === 0).length /
          latePreTrials.length
        : 0;

    // Post-reversal adaptation speed: first trial in post-reversal phase
    // where participant chooses arm 2 (new best) 3 consecutive times
    const postTrials = trials.filter((t) => t.phase === "post-reversal");
    let adaptationTrial: number | null = null;
    for (let i = 0; i <= postTrials.length - 3; i++) {
      if (
        postTrials[i].chosenArm === 2 &&
        postTrials[i + 1].chosenArm === 2 &&
        postTrials[i + 2].chosenArm === 2
      ) {
        adaptationTrial = postTrials[i].trialInPhase + 1; // 1-indexed
        break;
      }
    }

    // Win-stay ratio: after a win, how often do they repeat the same choice?
    let winStayCount = 0;
    let winCount = 0;
    let loseShiftCount = 0;
    let loseCount = 0;
    for (let i = 1; i < trials.length; i++) {
      const prev = trials[i - 1];
      if (prev.reward === 1) {
        winCount++;
        if (trials[i].chosenArm === prev.chosenArm) {
          winStayCount++;
        }
      } else {
        loseCount++;
        if (trials[i].chosenArm !== prev.chosenArm) {
          loseShiftCount++;
        }
      }
    }
    const winStayRatio = winCount > 0 ? winStayCount / winCount : 0;
    const loseShiftRatio = loseCount > 0 ? loseShiftCount / loseCount : 0;

    return {
      totalTrials: numTrials,
      completedTrials: trials.length,
      meanRT: Math.round(meanRT),
      accuracy: Math.round(preReversalAccuracy * 1000) / 1000,
      totalReward,
      preReversalAccuracy: Math.round(preReversalAccuracy * 1000) / 1000,
      adaptationTrial,
      winStayRatio: Math.round(winStayRatio * 1000) / 1000,
      loseShiftRatio: Math.round(loseShiftRatio * 1000) / 1000,
    };
  }, [numTrials, reversalTrial]);

  const advanceToNextTrial = useCallback(() => {
    const nextIndex = trialIndexRef.current + 1;
    if (nextIndex >= numTrials) {
      setPhase("done");
      const summary = computeSummary();
      onComplete(trialsRef.current, summary);
    } else {
      setTrialIndex(nextIndex);
      trialStartRef.current = performance.now();
      setPhase("fixation");
      setTimeout(startChoosePhase, 500);
    }
  }, [numTrials, onComplete, startChoosePhase, computeSummary]);

  const handleChoice = useCallback(
    (arm: 0 | 1 | 2) => {
      if (phaseRef.current !== "choose") return;

      const respondedAt = performance.now();
      const rt = respondedAt - stimulusOnsetRef.current;
      const currentIdx = trialIndexRef.current;
      const probs = getCurrentProbs(currentIdx);

      // Bernoulli reward
      const reward: 0 | 1 = Math.random() < probs[arm] ? 1 : 0;

      // Record trial with current Q-values (before update)
      const trialData: ReversalTrialData = {
        taskType: "reversal-learning",
        trialIndex: currentIdx,
        startedAt: trialStartRef.current,
        respondedAt,
        rt,
        stimulusOnsetAt: stimulusOnsetRef.current,
        chosenArm: arm,
        reward,
        rewardProbabilities: [...probs] as [number, number, number],
        qValues: [...qRef.current] as [number, number, number],
        phase: getPhaseLabel(currentIdx),
        trialInPhase: getTrialInPhase(currentIdx),
      };
      trialsRef.current.push(trialData);

      // Update Q-values with alpha=0.1
      const alpha = 0.1;
      const newQ: [number, number, number] = [...qRef.current];
      newQ[arm] = newQ[arm] + alpha * (reward - newQ[arm]);
      qRef.current = newQ;
      setQValues(newQ);

      // Update score and show feedback
      setScore((s) => s + reward);
      setLastReward(reward);
      setLastChosen(arm);
      setPhase("feedback");

      setTimeout(advanceToNextTrial, 1500);
    },
    [getCurrentProbs, getPhaseLabel, getTrialInPhase, advanceToNextTrial]
  );

  // Keyboard support
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (phaseRef.current !== "choose") return;
      if (e.key === "1") {
        handleChoice(0);
      } else if (e.key === "2") {
        handleChoice(1);
      } else if (e.key === "3") {
        handleChoice(2);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleChoice]);

  const progressPct = (trialIndex / numTrials) * 100;
  const currentPhaseLabel = getPhaseLabel(trialIndex);

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.title}>Reversal Learning</div>
        <div style={styles.scoreDisplay}>
          Score: <span style={styles.scoreValue}>{score}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div style={styles.progressSection}>
        <div style={styles.trialRow}>
          <div style={styles.trialLabel}>
            Trial {Math.min(trialIndex + 1, numTrials)} / {numTrials}
          </div>
          <div style={styles.phaseLabel}>
            {currentPhaseLabel === "pre-reversal" ? "Phase 1" : "Phase 2"}
          </div>
        </div>
        <div style={styles.progressTrack}>
          <div
            style={{
              ...styles.progressFill,
              width: `${progressPct}%`,
            }}
          />
          {/* Reversal marker */}
          <div
            style={{
              position: "absolute" as const,
              left: `${(reversalTrial / numTrials) * 100}%`,
              top: "-2px",
              width: "2px",
              height: "8px",
              background: "var(--danger)",
              borderRadius: "1px",
            }}
          />
        </div>
      </div>

      {/* Main area */}
      <div style={styles.mainArea}>
        {phase === "fixation" && (
          <div style={styles.fixation}>+</div>
        )}

        {phase === "choose" && (
          <div style={styles.choiceArea}>
            <div style={styles.instruction}>Choose a fishing spot</div>
            <div style={styles.armsRow}>
              <button
                style={styles.armButton1}
                onClick={() => handleChoice(0)}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.transform = "scale(1.06)";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    "0 0 24px rgba(240, 192, 96, 0.3)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.transform = "scale(1)";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    "0 0 0 transparent";
                }}
              >
                <div style={styles.armIcon}>&#x1F3A3;</div>
                <div style={styles.armLabel}>Spot 1</div>
                <div style={styles.armHint}>Press 1</div>
              </button>
              <button
                style={styles.armButton2}
                onClick={() => handleChoice(1)}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.transform = "scale(1.06)";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    "0 0 24px rgba(96, 168, 240, 0.3)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.transform = "scale(1)";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    "0 0 0 transparent";
                }}
              >
                <div style={styles.armIcon}>&#x1F3A3;</div>
                <div style={styles.armLabel}>Spot 2</div>
                <div style={styles.armHint}>Press 2</div>
              </button>
              <button
                style={styles.armButton3}
                onClick={() => handleChoice(2)}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.transform = "scale(1.06)";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    "0 0 24px rgba(96, 200, 144, 0.3)";
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.transform = "scale(1)";
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    "0 0 0 transparent";
                }}
              >
                <div style={styles.armIcon}>&#x1F3A3;</div>
                <div style={styles.armLabel}>Spot 3</div>
                <div style={styles.armHint}>Press 3</div>
              </button>
            </div>
          </div>
        )}

        {phase === "feedback" && (
          <div style={styles.feedbackArea}>
            <div
              style={{
                ...styles.feedbackText,
                color:
                  lastReward === 1
                    ? "var(--success)"
                    : "var(--danger)",
              }}
            >
              {lastReward === 1 ? "+1" : "0"}
            </div>
            <div style={styles.feedbackSubtext}>
              You chose Spot {lastChosen !== null ? lastChosen + 1 : "?"}
            </div>
          </div>
        )}

        {phase === "done" && (
          <div style={styles.doneArea}>
            <div style={styles.doneTitle}>Task Complete</div>
            <div style={styles.doneScore}>
              Final Score: {score} / {numTrials}
            </div>
          </div>
        )}
      </div>

      {/* Q-value display (subtle) */}
      <div style={styles.qDisplay}>
        <span style={styles.qLabel}>Q-values:</span>
        <span style={{ color: "var(--accent)" }}>
          Q1 = {qValues[0].toFixed(3)}
        </span>
        <span style={{ color: "var(--muted)", margin: "0 6px" }}>|</span>
        <span style={{ color: "var(--accent2)" }}>
          Q2 = {qValues[1].toFixed(3)}
        </span>
        <span style={{ color: "var(--muted)", margin: "0 6px" }}>|</span>
        <span style={{ color: "var(--success)" }}>
          Q3 = {qValues[2].toFixed(3)}
        </span>
      </div>
    </div>
  );
}

// --- Inline styles using CSS vars ---

const armButtonBase: React.CSSProperties = {
  width: "130px",
  height: "140px",
  borderRadius: "16px",
  background: "var(--surface)",
  cursor: "pointer",
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  justifyContent: "center",
  gap: "8px",
  transition: "transform 0.15s ease, box-shadow 0.15s ease",
  fontFamily: "'IBM Plex Mono', monospace",
};

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    minHeight: "100vh",
    width: "100%",
    background: "var(--bg)",
    color: "var(--text)",
    fontFamily: "'IBM Plex Mono', monospace",
    padding: "24px",
    boxSizing: "border-box",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    width: "100%",
    maxWidth: "560px",
    marginBottom: "16px",
  },
  title: {
    fontFamily: "'Syne', sans-serif",
    fontWeight: 700,
    fontSize: "18px",
    color: "var(--accent)",
    letterSpacing: "0.04em",
  },
  scoreDisplay: {
    fontSize: "13px",
    color: "var(--muted)",
  },
  scoreValue: {
    color: "var(--accent)",
    fontWeight: 600,
  },
  progressSection: {
    width: "100%",
    maxWidth: "560px",
    marginBottom: "32px",
  },
  trialRow: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: "6px",
  },
  trialLabel: {
    fontSize: "11px",
    color: "var(--muted)",
    letterSpacing: "0.1em",
    textTransform: "uppercase" as const,
  },
  phaseLabel: {
    fontSize: "10px",
    color: "var(--accent2)",
    letterSpacing: "0.08em",
    textTransform: "uppercase" as const,
  },
  progressTrack: {
    width: "100%",
    height: "4px",
    background: "var(--border)",
    borderRadius: "2px",
    overflow: "visible",
    position: "relative" as const,
  },
  progressFill: {
    height: "100%",
    background: "var(--accent)",
    borderRadius: "2px",
    transition: "width 0.3s ease",
  },
  mainArea: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    width: "100%",
    maxWidth: "560px",
    minHeight: "280px",
  },
  fixation: {
    fontSize: "48px",
    fontWeight: 300,
    color: "var(--muted)",
    userSelect: "none" as const,
  },
  choiceArea: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "24px",
    width: "100%",
  },
  instruction: {
    fontSize: "13px",
    color: "var(--muted)",
    letterSpacing: "0.06em",
  },
  armsRow: {
    display: "flex",
    gap: "24px",
    justifyContent: "center",
  },
  armButton1: {
    ...armButtonBase,
    border: "2px solid var(--accent)",
    color: "var(--accent)",
  },
  armButton2: {
    ...armButtonBase,
    border: "2px solid var(--accent2)",
    color: "var(--accent2)",
  },
  armButton3: {
    ...armButtonBase,
    border: "2px solid var(--success)",
    color: "var(--success)",
  },
  armIcon: {
    fontSize: "32px",
  },
  armLabel: {
    fontSize: "12px",
    fontWeight: 500,
    fontFamily: "'Syne', sans-serif",
  },
  armHint: {
    fontSize: "10px",
    opacity: 0.5,
    letterSpacing: "0.05em",
  },
  feedbackArea: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "12px",
  },
  feedbackText: {
    fontSize: "64px",
    fontWeight: 700,
    fontFamily: "'Syne', sans-serif",
  },
  feedbackSubtext: {
    fontSize: "12px",
    color: "var(--muted)",
  },
  doneArea: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "12px",
  },
  doneTitle: {
    fontFamily: "'Syne', sans-serif",
    fontSize: "24px",
    fontWeight: 700,
    color: "var(--success)",
  },
  doneScore: {
    fontSize: "14px",
    color: "var(--muted)",
  },
  qDisplay: {
    marginTop: "24px",
    fontSize: "11px",
    color: "var(--muted)",
    letterSpacing: "0.04em",
  },
  qLabel: {
    marginRight: "8px",
    opacity: 0.6,
  },
};
