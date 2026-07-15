"use client";

import { useState } from "react";
import { ComprehensionQuestion } from "@/lib/types";

interface ComprehensionCheckProps {
  questions: ComprehensionQuestion[];
  onComplete: () => void;
  title?: string;
}

export default function ComprehensionCheck({ questions, onComplete, title }: ComprehensionCheckProps) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);

  const allAnswered = questions.every((q) => answers[q.id] !== undefined && answers[q.id] !== "");

  function handleMcSelect(questionId: string, optionId: string) {
    if (submitted) return;
    setAnswers((prev) => ({ ...prev, [questionId]: optionId }));
  }

  function handleTextChange(questionId: string, value: string) {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  }

  function handleSubmit() {
    setSubmitted(true);
  }

  function isCorrect(question: ComprehensionQuestion): boolean {
    const selected = answers[question.id];
    return question.options?.find((o) => o.id === selected)?.correct ?? false;
  }

  return (
    <div className="quiz-card">
        <div className="start-tag" style={{ marginBottom: 8 }}>Comprehension Check</div>
        <h2 style={{ fontFamily: "Syne, sans-serif", fontSize: 20, fontWeight: 700, color: "var(--text)", marginBottom: 6 }}>
          {title ?? "Before you move on"}
        </h2>
        <p style={{ fontSize: 12, color: "var(--muted)", lineHeight: 1.7, marginBottom: 28 }}>
          Quick check on what was decided in the meeting.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 28 }}>
          {questions.map((q, qi) => (
            <div key={q.id}>
              <p style={{ fontSize: 13, color: "var(--text)", lineHeight: 1.6, marginBottom: 12, fontWeight: 500 }}>
                {qi + 1}. {q.prompt}
              </p>

              {q.type === "mc" && q.options && (
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {q.options.map((opt) => {
                    const selected = answers[q.id] === opt.id;
                    let bg = "var(--surface2)";
                    let border = "var(--border)";
                    let color = "var(--muted)";

                    if (submitted) {
                      if (opt.correct) { bg = "rgba(96,200,144,0.12)"; border = "var(--success)"; color = "var(--success)"; }
                      else if (selected && !opt.correct) { bg = "rgba(240,96,96,0.1)"; border = "var(--danger)"; color = "var(--danger)"; }
                    } else if (selected) {
                      border = "var(--accent)";
                      color = "var(--accent)";
                      bg = "rgba(240,192,96,0.08)";
                    }

                    return (
                      <button
                        key={opt.id}
                        onClick={() => handleMcSelect(q.id, opt.id)}
                        style={{
                          background: bg,
                          border: `1px solid ${border}`,
                          borderRadius: 8,
                          padding: "10px 14px",
                          color,
                          fontFamily: "IBM Plex Mono, monospace",
                          fontSize: 12,
                          textAlign: "left",
                          cursor: submitted ? "default" : "pointer",
                          transition: "border-color 0.2s, color 0.2s",
                          lineHeight: 1.5,
                        }}
                      >
                        <span style={{ opacity: 0.5, marginRight: 8 }}>{opt.id.toUpperCase()})</span>
                        {opt.text}
                        {submitted && opt.correct && <span style={{ marginLeft: 8, fontSize: 11 }}>✓ Correct</span>}
                        {submitted && selected && !opt.correct && <span style={{ marginLeft: 8, fontSize: 11 }}>✗</span>}
                      </button>
                    );
                  })}

                  {submitted && (
                    <p style={{ fontSize: 11, color: isCorrect(q) ? "var(--success)" : "var(--danger)", marginTop: 4 }}>
                      {isCorrect(q) ? "Correct!" : `The correct answer is highlighted above.`}
                    </p>
                  )}
                </div>
              )}

              {q.type === "openended" && (
                <textarea
                  value={answers[q.id] ?? ""}
                  onChange={(e) => handleTextChange(q.id, e.target.value)}
                  disabled={submitted}
                  placeholder="Type your answer..."
                  rows={3}
                  style={{
                    width: "100%",
                    background: "var(--surface2)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    padding: "10px 12px",
                    color: "var(--text)",
                    fontFamily: "IBM Plex Mono, monospace",
                    fontSize: 12,
                    outline: "none",
                    lineHeight: 1.6,
                    resize: "vertical",
                    opacity: submitted ? 0.7 : 1,
                  }}
                />
              )}
            </div>
          ))}
        </div>

        <div style={{ marginTop: 28, display: "flex", gap: 12, alignItems: "center" }}>
          {!submitted ? (
            <button
              className="start-btn"
              onClick={handleSubmit}
              disabled={!allAnswered}
              style={{ fontSize: 13, opacity: allAnswered ? 1 : 0.4 }}
            >
              Submit Answers
            </button>
          ) : (
            <>
              <p style={{ fontSize: 12, color: "var(--muted)", flex: 1 }}>
                Answers recorded. Ready to move to the prototype review.
              </p>
              <button className="start-btn" onClick={onComplete} style={{ fontSize: 13 }}>
                Continue →
              </button>
            </>
          )}
        </div>
      </div>
  );
}
