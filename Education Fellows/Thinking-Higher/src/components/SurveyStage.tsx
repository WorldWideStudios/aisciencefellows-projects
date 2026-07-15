"use client";

import { useState } from "react";
import type { SurveyQuestion, SurveyResponse } from "@/lib/types";

interface Props {
  stageLabel: string;
  questions: SurveyQuestion[];
  onComplete: (responses: SurveyResponse[]) => void;
}

const DEFAULT_LIKERT_LABELS = [
  "Strongly Disagree",
  "Disagree",
  "Neutral",
  "Agree",
  "Strongly Agree",
];

export default function SurveyStage({ stageLabel, questions, onComplete }: Props) {
  const [answers, setAnswers] = useState<Record<string, number | string>>({});

  const requiredCount = questions.filter((q) => q.type === "likert").length;
  const answeredCount = questions.filter(
    (q) => q.type === "likert" && answers[q.id] !== undefined
  ).length;
  const canSubmit = answeredCount >= requiredCount;

  const setAnswer = (questionId: string, value: number | string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = () => {
    if (!canSubmit) return;
    const responses: SurveyResponse[] = questions
      .filter((q) => answers[q.id] !== undefined && answers[q.id] !== "")
      .map((q) => ({
        questionId: q.id,
        value: answers[q.id],
        answeredAt: Date.now(),
      }));
    onComplete(responses);
  };

  return (
    <div className="survey-stage">
      <div className="survey-card">
        <div className="survey-tag">Quick Reflection</div>
        <h2 className="survey-title">How did that conversation go?</h2>
        <p className="survey-desc">
          Reflect on your conversation with {stageLabel}. There are no right or wrong answers.
        </p>

        <div className="survey-questions">
          {questions.map((q) => (
            <div key={q.id} className="survey-question">
              <div className="survey-prompt">{q.prompt}</div>
              {q.type === "likert" ? (
                <div className="likert-row">
                  {(q.likertLabels || DEFAULT_LIKERT_LABELS).map((label, i) => (
                    <button
                      key={i}
                      className={`likert-btn ${answers[q.id] === i + 1 ? "selected" : ""}`}
                      onClick={() => setAnswer(q.id, i + 1)}
                      title={label}
                    >
                      <span className="likert-num">{i + 1}</span>
                      <span className="likert-label">{label}</span>
                    </button>
                  ))}
                </div>
              ) : (
                <textarea
                  className="profile-input profile-textarea"
                  placeholder="Your thoughts..."
                  value={(answers[q.id] as string) || ""}
                  onChange={(e) => setAnswer(q.id, e.target.value)}
                  rows={3}
                  maxLength={1000}
                />
              )}
            </div>
          ))}
        </div>

        <button
          className="start-btn"
          onClick={handleSubmit}
          disabled={!canSubmit}
          style={{ opacity: canSubmit ? 1 : 0.4, marginTop: 16 }}
        >
          Continue
        </button>
      </div>
    </div>
  );
}
