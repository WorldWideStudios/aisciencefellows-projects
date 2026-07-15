"use client";

import { useState } from "react";
import type { ProfileData } from "@/lib/types";

interface Props {
  onComplete: (profile: ProfileData) => void;
}

const EXPERIENCE_OPTIONS = [
  { value: "student", label: "Student" },
  { value: "early-career", label: "Early Career (0-2 years)" },
  { value: "mid-career", label: "Mid Career (3-7 years)" },
  { value: "senior", label: "Senior (8+ years)" },
];

export default function ProfileStage({ onComplete }: Props) {
  const [displayName, setDisplayName] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("");
  const [goal, setGoal] = useState("");

  const canSubmit = displayName.trim() && experienceLevel;

  const handleSubmit = () => {
    if (!canSubmit) return;
    onComplete({
      displayName: displayName.trim(),
      experienceLevel,
      goal: goal.trim(),
      submittedAt: Date.now(),
    });
  };

  return (
    <div className="profile-stage">
      <div className="profile-card">
        <div className="profile-tag">Before we begin</div>
        <h2 className="profile-title">Tell us about yourself</h2>
        <p className="profile-desc">
          This helps us tailor the simulation and contextualize your results.
        </p>

        <div className="profile-field">
          <label className="profile-label">Display Name</label>
          <input
            className="profile-input"
            type="text"
            placeholder="How should the team address you?"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            maxLength={40}
            autoFocus
          />
        </div>

        <div className="profile-field">
          <label className="profile-label">Experience Level</label>
          <div className="profile-options">
            {EXPERIENCE_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                className={`profile-option ${experienceLevel === opt.value ? "selected" : ""}`}
                onClick={() => setExperienceLevel(opt.value)}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        <div className="profile-field">
          <label className="profile-label">
            What do you hope to learn? <span className="optional">(optional)</span>
          </label>
          <textarea
            className="profile-input profile-textarea"
            placeholder="e.g., I want to get better at explaining technical issues to non-technical stakeholders..."
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            rows={3}
            maxLength={500}
          />
        </div>

        <button
          className="start-btn"
          onClick={handleSubmit}
          disabled={!canSubmit}
          style={{ opacity: canSubmit ? 1 : 0.4, marginTop: 8 }}
        >
          Continue to Simulation
        </button>
      </div>
    </div>
  );
}
