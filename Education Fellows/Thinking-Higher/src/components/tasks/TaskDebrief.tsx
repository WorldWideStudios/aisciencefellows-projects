"use client";

import CentaurComparison from "./CentaurComparison";
import type { CentaurComparisonResult } from "./CentaurComparison";

interface TaskSummary {
  totalTrials: number;
  completedTrials: number;
  meanRT: number;
  accuracy?: number;
  [key: string]: unknown;
}

interface TaskDebriefProps {
  title: string;
  debriefText: string;
  summary: TaskSummary;
  taskType: string;
  rwFit?: { alpha: number; tau: number; qValuesOverTime: [number, number][] };
  trials?: any[];
  comparisonResult?: CentaurComparisonResult | null;
  comparisonLoading?: boolean;
  onContinue: () => void;
}

function formatMs(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)}ms` : `${(ms / 1000).toFixed(1)}s`;
}

function alphaDescription(alpha: number): string {
  if (alpha < 0.2) return "You update beliefs slowly, weighting older experiences heavily.";
  if (alpha < 0.5) return "You have a moderate learning rate, balancing old and new information.";
  return "You update beliefs quickly, strongly influenced by recent outcomes.";
}

function tauDescription(tau: number): string {
  if (tau < 1) return "You explored a lot, trying both options frequently.";
  if (tau < 3) return "You balanced exploration and exploitation moderately.";
  return "You exploited heavily, consistently picking the higher-valued option.";
}

export default function TaskDebrief({
  title,
  debriefText,
  summary,
  taskType,
  rwFit,
  comparisonResult,
  comparisonLoading,
  onContinue,
}: TaskDebriefProps) {
  return (
    <div className="task-container">
      <div className="task-card">
        <div className="task-tag">RESULTS</div>
        <h1 className="task-title">{title}</h1>

        <div className="task-stats">
          <div className="task-stat">
            <div className="task-stat-value">
              {summary.completedTrials}/{summary.totalTrials}
            </div>
            <div className="task-stat-label">Trials Completed</div>
          </div>
          <div className="task-stat">
            <div className="task-stat-value">{formatMs(summary.meanRT)}</div>
            <div className="task-stat-label">Mean Response Time</div>
          </div>
          {summary.accuracy !== undefined && (
            <div className="task-stat">
              <div className="task-stat-value">
                {Math.round(summary.accuracy * 100)}%
              </div>
              <div className="task-stat-label">Accuracy</div>
            </div>
          )}
        </div>

        {taskType === "two-armed-bandit" && rwFit && (
          <div style={{ marginBottom: 24 }}>
            <div
              className="task-tag"
              style={{ marginBottom: 16, marginTop: 8 }}
            >
              MODEL FIT: RESCORLA-WAGNER
            </div>

            <div className="task-stats">
              <div className="task-stat">
                <div className="task-stat-value">
                  {rwFit.alpha.toFixed(3)}
                </div>
                <div className="task-stat-label">Learning Rate (alpha)</div>
              </div>
              <div className="task-stat">
                <div className="task-stat-value">{rwFit.tau.toFixed(3)}</div>
                <div className="task-stat-label">
                  Inverse Temperature (tau)
                </div>
              </div>
            </div>

            <div
              style={{
                background: "var(--surface2)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: 14,
                marginTop: 12,
              }}
            >
              <p
                style={{
                  fontSize: "11px",
                  lineHeight: 1.7,
                  color: "var(--muted)",
                  marginBottom: 8,
                }}
              >
                <strong style={{ color: "var(--accent)" }}>
                  Learning rate ({rwFit.alpha.toFixed(3)}):
                </strong>{" "}
                {alphaDescription(rwFit.alpha)}
              </p>
              <p
                style={{
                  fontSize: "11px",
                  lineHeight: 1.7,
                  color: "var(--muted)",
                }}
              >
                <strong style={{ color: "var(--accent)" }}>
                  Exploration tendency ({rwFit.tau.toFixed(3)}):
                </strong>{" "}
                {tauDescription(rwFit.tau)}
              </p>
            </div>

            {rwFit.qValuesOverTime.length > 0 && (
              <div style={{ marginTop: 16 }}>
                <div
                  className="task-tag"
                  style={{ marginBottom: 8 }}
                >
                  Q-VALUE TRAJECTORY
                </div>
                <div
                  style={{
                    background: "var(--surface2)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: "14px 14px 10px",
                    fontFamily: "'IBM Plex Mono', monospace",
                    fontSize: "10px",
                    lineHeight: 1.4,
                    color: "var(--muted)",
                    overflowX: "auto",
                  }}
                >
                  {(() => {
                    const qvs = rwFit.qValuesOverTime;
                    const step = Math.max(1, Math.floor(qvs.length / 20));
                    const sampled = qvs.filter((_, i) => i % step === 0 || i === qvs.length - 1);
                    return (
                      <div style={{ display: "flex", gap: 2, alignItems: "flex-end", height: 60 }}>
                        {sampled.map(([q1, q2], idx) => {
                          const maxQ = Math.max(q1, q2, 0.01);
                          const h1 = Math.round((q1 / 1) * 50);
                          const h2 = Math.round((q2 / 1) * 50);
                          return (
                            <div key={idx} style={{ display: "flex", gap: 1, alignItems: "flex-end" }}>
                              <div
                                style={{
                                  width: 4,
                                  height: Math.max(2, h1),
                                  background: "var(--accent2)",
                                  borderRadius: 1,
                                }}
                                title={`Arm 1: ${q1.toFixed(2)}`}
                              />
                              <div
                                style={{
                                  width: 4,
                                  height: Math.max(2, h2),
                                  background: "var(--accent)",
                                  borderRadius: 1,
                                }}
                                title={`Arm 2: ${q2.toFixed(2)}`}
                              />
                            </div>
                          );
                        })}
                      </div>
                    );
                  })()}
                  <div
                    style={{
                      display: "flex",
                      gap: 12,
                      marginTop: 6,
                      fontSize: "9px",
                    }}
                  >
                    <span>
                      <span
                        style={{
                          display: "inline-block",
                          width: 8,
                          height: 8,
                          background: "var(--accent2)",
                          borderRadius: 2,
                          marginRight: 4,
                          verticalAlign: "middle",
                        }}
                      />
                      Arm 1
                    </span>
                    <span>
                      <span
                        style={{
                          display: "inline-block",
                          width: 8,
                          height: 8,
                          background: "var(--accent)",
                          borderRadius: 2,
                          marginRight: 4,
                          verticalAlign: "middle",
                        }}
                      />
                      Arm 2
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <p className="task-text">{debriefText}</p>

        <CentaurComparison
          result={comparisonResult ?? null}
          loading={comparisonLoading}
          taskType={taskType}
        />

        <button className="start-btn" onClick={onContinue}>
          Continue
        </button>
      </div>
    </div>
  );
}
