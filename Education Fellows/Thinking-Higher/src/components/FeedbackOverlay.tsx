"use client";

import { EvaluationResult, SkillDimension } from "@/lib/types";

interface FeedbackOverlayProps {
  visible: boolean;
  result: EvaluationResult | null;
  dimensions: SkillDimension[];
  subtitle: string;
  onClose: () => void;
}

// CPS sub-domains shown under "Problem Solving"
const PROBLEM_SOLVING_KEYS = new Set(["originality", "quality", "elaboration"]);

function DimensionCard({ dim, result, index }: {
  dim: SkillDimension;
  result: EvaluationResult | null;
  index: number;
}) {
  const detail = result?.dimensionDetail?.[dim.key];
  const score = detail?.score ?? result?.scores[dim.key] ?? 0;

  return (
    <div className="dimension-card">
      <div className="skill-bar">
        <span className="skill-name">{dim.label}</span>
        <div className="skill-track">
          <div
            className="skill-fill"
            style={{ width: `${score}%`, transitionDelay: `${0.15 * index}s` }}
          />
        </div>
        <span className="skill-score">{result ? score : "—"}</span>
      </div>

      {detail?.quote && (
        <blockquote className="evidence-quote">
          <p>&ldquo;{detail.quote}&rdquo;</p>
          {detail.badge && <cite className="evidence-badge">↳ {detail.badge}</cite>}
        </blockquote>
      )}

      {detail?.narrative && (
        <p className="dimension-narrative">{detail.narrative}</p>
      )}
    </div>
  );
}

export default function FeedbackOverlay({
  visible, result, dimensions, subtitle, onClose,
}: FeedbackOverlayProps) {
  if (!visible) return null;

  const problemSolving = dimensions.filter(d => PROBLEM_SOLVING_KEYS.has(d.key));
  const processSkills = dimensions.filter(d => !PROBLEM_SOLVING_KEYS.has(d.key));
  const isDetailed = !!result?.dimensionDetail;

  return (
    <div className="feedback-overlay visible">
      <div className="feedback-card">
        <div className="feedback-title">Simulation Complete</div>
        <div className="feedback-subtitle">{subtitle}</div>

        {isDetailed ? (
          <>
            <div className="feedback-section">
              <div className="feedback-section-title">Problem Solving</div>
              {problemSolving.map((d, i) => (
                <DimensionCard key={d.key} dim={d} result={result} index={i} />
              ))}
            </div>
            <div className="feedback-section">
              <div className="feedback-section-title">Process Skills</div>
              {processSkills.map((d, i) => (
                <DimensionCard key={d.key} dim={d} result={result} index={problemSolving.length + i} />
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="feedback-section">
              <div className="feedback-section-title">Skills Evaluated</div>
              {dimensions.map((d, i) => {
                const score = result?.scores[d.key] ?? 0;
                return (
                  <div key={d.key} className="skill-bar">
                    <span className="skill-name">{d.label}</span>
                    <div className="skill-track">
                      <div
                        className="skill-fill"
                        style={{ width: `${score}%`, transitionDelay: `${0.2 * i}s` }}
                      />
                    </div>
                    <span className="skill-score">{result ? score : "—"}</span>
                  </div>
                );
              })}
            </div>
            <div className="feedback-section">
              <div className="feedback-section-title">Overall Feedback</div>
              <div className="feedback-text">
                {result?.feedback || "Generating your feedback..."}
              </div>
            </div>
          </>
        )}

        <button className="close-feedback" onClick={onClose}>
          Close &amp; Review Conversation
        </button>
      </div>
    </div>
  );
}
