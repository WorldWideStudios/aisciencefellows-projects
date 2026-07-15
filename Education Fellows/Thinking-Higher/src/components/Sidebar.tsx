"use client";

import { STAGES } from "@/lib/scenarios";
import { StageV2Runtime } from "@/lib/types";

interface SidebarProps {
  currentStage: number;
  simulationComplete: boolean;
  completedStages: Set<number>;
  visitedStages: Set<number>;
  onReviewStage: (index: number) => void;
  stagesV2?: StageV2Runtime[];
  contextText?: string;
}

export default function Sidebar({
  currentStage,
  simulationComplete,
  completedStages,
  visitedStages,
  onReviewStage,
  stagesV2,
  contextText,
}: SidebarProps) {
  // V2 stages take priority; fall back to Vela V1 stages
  const isV2 = !!stagesV2;
  const stageList = isV2
    ? stagesV2!.map((s) => ({
        id: s.id,
        color: s.agent.color,
        stageTitle: s.title,
        avatarLetter: s.agent.avatar,
      }))
    : STAGES.map((s) => ({
        id: s.id,
        color: s.color,
        stageTitle: s.stageTitle,
        avatarLetter: s.id.charAt(0).toUpperCase(),
      }));

  const defaultContext = isV2
    ? null
    : "You are a junior SDE in your second week at Vela, an IT asset management company. Your team is building the customer onboarding module this sprint — and you're leading the build.";

  const shownContext = contextText ?? defaultContext;

  return (
    <div className="sidebar">
      <div className="sidebar-section">
        <div className="sidebar-label">Stages</div>
        {stageList.map((stage, i) => {
          const isDone = completedStages.has(i) || visitedStages.has(i) || simulationComplete;
          const isActive = i === currentStage;
          const classes = [
            "stakeholder",
            isDone ? "done-stakeholder" : "",
            isActive ? "active-stakeholder" : "",
          ].filter(Boolean).join(" ");

          return (
            <div
              key={stage.id}
              className={classes}
              onClick={isDone ? () => onReviewStage(i) : undefined}
            >
              <div
                className="stakeholder-avatar"
                style={{
                  background: isActive ? `${stage.color}22` : "var(--surface2)",
                  color: isActive ? stage.color : "var(--muted)",
                  fontSize: 10,
                  fontWeight: 700,
                  letterSpacing: "0.02em",
                }}
              >
                {(completedStages.has(i) || simulationComplete) ? "✓" : `0${i + 1}`}
              </div>
              <div className="stakeholder-info">
                <div className="stakeholder-name">{stage.stageTitle}</div>
              </div>
            </div>
          );
        })}
      </div>
      {shownContext && (
        <div className="sidebar-section">
          <div className="context-box">
            <strong>Your Context</strong>
            {shownContext}
          </div>
        </div>
      )}
    </div>
  );
}
