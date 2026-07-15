"use client";

import React, { useState, useRef, useCallback, useEffect } from "react";
import type { BanditTrialData, TaskSummary } from "@/lib/types";

interface TwoArmedBanditProps {
  numTrials?: number;
  rewardProbabilities?: [number, number];
  onComplete: (trials: BanditTrialData[], summary: TaskSummary) => void;
}

type Phase = "fixation" | "choose" | "feedback" | "done";

export default function TwoArmedBandit({
  numTrials = 80,
  rewardProbabilities = [0.7, 0.3],
  onComplete,
}: TwoArmedBanditProps) {
  const [phase, setPhase] = useState<Phase>("fixation");
  const [trialIndex, setTrialIndex] = useState(0);
  const [score, setScore] = useState(0);
  const [lastReward, setLastReward] = useState<0 | 1 | null>(null);
  const [lastChosen, setLastChosen] = useState<0 | 1 | null>(null);
  const [qValues, setQValues] = useState<[number, number]>([0.5, 0.5]);

  const trialsRef = useRef<BanditTrialData[]>([]);
  const qRef = useRef<[number, number]>([0.5, 0.5]);
  const trialStartRef = useRef(0);
  const stimulusOnsetRef = useRef(0);
  const phaseRef = useRef<Phase>("fixation");
  const trialIndexRef = useRef(0);

  // Keep refs in sync with state
  phaseRef.current = phase;
  trialIndexRef.current = trialIndex;

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

  const advanceToNextTrial = useCallback(() => {
    const nextIndex = trialIndexRef.current + 1;
    if (nextIndex >= numTrials) {
      setPhase("done");
      // Compute summary
      const trials = trialsRef.current;
      const rts = trials.map((t) => t.rt);
      const meanRT = rts.reduce((a, b) => a + b, 0) / rts.length;
      // Accuracy: fraction of trials where participant chose the higher-probability arm
      const betterArm = rewardProbabilities[0] >= rewardProbabilities[1] ? 0 : 1;
      const correctChoices = trials.filter(
        (t) => t.chosenArm === betterArm
      ).length;
      const accuracy = correctChoices / trials.length;
      const totalReward = trials.reduce((a, t) => a + t.reward, 0);

      const summary: TaskSummary = {
        totalTrials: numTrials,
        completedTrials: trials.length,
        meanRT: Math.round(meanRT),
        accuracy: Math.round(accuracy * 1000) / 1000,
        totalReward,
        optimalArm: betterArm,
      };
      onComplete(trials, summary);
    } else {
      setTrialIndex(nextIndex);
      trialStartRef.current = performance.now();
      setPhase("fixation");
      setTimeout(startChoosePhase, 500);
    }
  }, [numTrials, rewardProbabilities, onComplete, startChoosePhase]);

  const handleChoice = useCallback(
    (arm: 0 | 1) => {
      if (phaseRef.current !== "choose") return;

      const respondedAt = performance.now();
      const rt = respondedAt - stimulusOnsetRef.current;

      // Bernoulli reward
      const reward: 0 | 1 = Math.random() < rewardProbabilities[arm] ? 1 : 0;

      // Record trial with current Q-values (before update)
      const trialData: BanditTrialData = {
        taskType: "two-armed-bandit",
        trialIndex: trialIndexRef.current,
        startedAt: trialStartRef.current,
        respondedAt,
        rt,
        stimulusOnsetAt: stimulusOnsetRef.current,
        chosenArm: arm,
        reward,
        rewardProbabilities: [...rewardProbabilities] as [number, number],
        qValues: [...qRef.current] as [number, number],
      };
      trialsRef.current.push(trialData);

      // Update Q-values with alpha=0.1
      const alpha = 0.1;
      const newQ: [number, number] = [...qRef.current];
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
    [rewardProbabilities, advanceToNextTrial]
  );

  // Keyboard support
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (phaseRef.current !== "choose") return;
      if (e.key === "1" || e.key === "ArrowLeft") {
        handleChoice(0);
      } else if (e.key === "2" || e.key === "ArrowRight") {
        handleChoice(1);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handleChoice]);

  const progressPct = ((trialIndex + (phase === "done" ? 0 : 0)) / numTrials) * 100;

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.title}>Two-Armed Bandit</div>
        <div style={styles.scoreDisplay}>
          Score: <span style={styles.scoreValue}>{score}</span>
        </div>
      </div>

      {/* Progress bar */}
      <div style={styles.progressSection}>
        <div style={styles.trialLabel}>
          Trial {Math.min(trialIndex + 1, numTrials)} / {numTrials}
        </div>
        <div style={styles.progressTrack}>
          <div
            style={{
              ...styles.progressFill,
              width: `${progressPct}%`,
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
            <div style={styles.instruction}>Choose an arm</div>
            <div style={styles.armsRow}>
              <button
                style={styles.armButtonLeft}
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
                <div style={styles.armIcon}>L</div>
                <div style={styles.armLabel}>Arm 1</div>
                <div style={styles.armHint}>1 / Left</div>
              </button>
              <button
                style={styles.armButtonRight}
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
                <div style={styles.armIcon}>R</div>
                <div style={styles.armLabel}>Arm 2</div>
                <div style={styles.armHint}>2 / Right</div>
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
              You chose Arm {lastChosen !== null ? lastChosen + 1 : "?"}
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
      </div>
    </div>
  );
}

// --- Inline styles using CSS vars ---

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
    maxWidth: "520px",
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
    maxWidth: "520px",
    marginBottom: "32px",
  },
  trialLabel: {
    fontSize: "11px",
    color: "var(--muted)",
    letterSpacing: "0.1em",
    textTransform: "uppercase" as const,
    marginBottom: "6px",
  },
  progressTrack: {
    width: "100%",
    height: "4px",
    background: "var(--border)",
    borderRadius: "2px",
    overflow: "hidden",
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
    maxWidth: "520px",
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
    gap: "40px",
    justifyContent: "center",
  },
  armButtonLeft: {
    width: "140px",
    height: "140px",
    borderRadius: "16px",
    border: "2px solid var(--accent)",
    background: "var(--surface)",
    color: "var(--accent)",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    transition: "transform 0.15s ease, box-shadow 0.15s ease",
    fontFamily: "'IBM Plex Mono', monospace",
  },
  armButtonRight: {
    width: "140px",
    height: "140px",
    borderRadius: "16px",
    border: "2px solid var(--accent2)",
    background: "var(--surface)",
    color: "var(--accent2)",
    cursor: "pointer",
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: "8px",
    transition: "transform 0.15s ease, box-shadow 0.15s ease",
    fontFamily: "'IBM Plex Mono', monospace",
  },
  armIcon: {
    fontFamily: "'Syne', sans-serif",
    fontSize: "32px",
    fontWeight: 700,
  },
  armLabel: {
    fontSize: "12px",
    fontWeight: 500,
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
