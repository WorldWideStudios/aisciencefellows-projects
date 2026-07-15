"use client";

import { useState } from "react";
import { SituationBriefData } from "@/lib/types";

interface SituationBriefProps {
  data: SituationBriefData;
  defaultCollapsed?: boolean;
  userProfile?: { name: string; icon: string };
}

function renderContext(text: string) {
  // Bold **text** patterns
  return text.split(/(\*\*[^*]+\*\*)/).map((part, i) =>
    part.startsWith("**") ? (
      <strong key={i} style={{ color: "var(--text)", fontWeight: 600 }}>
        {part.slice(2, -2)}
      </strong>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

export default function SituationBrief({ data, defaultCollapsed = false, userProfile }: SituationBriefProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <div className="situation-brief">
      {/* Header */}
      <div className="brief-header" onClick={() => setCollapsed((c) => !c)}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div className="brief-icon">📋</div>
          <span className="brief-label">Situation Brief</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 11, color: "var(--muted)" }}>
          <span>{collapsed ? "Show" : "Hide"}</span>
          <span
            style={{
              display: "inline-block",
              transition: "transform 0.2s",
              transform: collapsed ? "rotate(0deg)" : "rotate(180deg)",
            }}
          >
            ▾
          </span>
        </div>
      </div>

      {/* Body */}
      {!collapsed && (
        <div className="brief-body">
          {/* Context */}
          <div className="brief-section">
            <div className="brief-section-label">Context</div>
            <p className="brief-context-text">{renderContext(data.context)}</p>
          </div>

          {/* Participants */}
          <div className="brief-section">
            <div className="brief-section-label">Who&apos;s in the room</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
              {data.participants.map((p) => {
                const displayName = p.isYou && userProfile ? userProfile.name : p.name;
                const icon = p.isYou && userProfile ? userProfile.icon : null;
                return (
                  <div key={p.name} className="participant-chip">
                    <div
                      className="p-avatar"
                      style={{
                        background: p.avatarColor ?? "var(--muted)",
                        fontSize: icon ? 14 : undefined,
                      }}
                    >
                      {icon ?? displayName[0]}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div className="p-name">{displayName}</div>
                      <div className="p-role">{p.role}</div>
                    </div>
                    {p.isYou && <span className="p-you-badge">You</span>}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Goal + Hints — full width */}
          <div className="goal-box">
            <div className="goal-icon">🎯</div>
            <div>
              <div className="goal-title">Your Goal</div>
              <p className="goal-text">{data.goal}</p>
              {data.hints.length > 0 && (
                <div className="goal-hints">
                  {data.hints.map((h, i) => (
                    <span key={i} className="hint-tag">💡 {h}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
