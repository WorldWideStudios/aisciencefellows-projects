"use client";

import FeedbackOverlay from "@/components/FeedbackOverlay";
import { EvaluationResult, SkillDimension } from "@/lib/types";

const DIMENSIONS: SkillDimension[] = [
  { key: "originality", label: "Originality", weight: 1 },
  { key: "quality", label: "Quality", weight: 1 },
  { key: "elaboration", label: "Elaboration", weight: 1 },
  { key: "critical_thinking", label: "Analytical Thinking", weight: 1 },
  { key: "information_processing", label: "Information Processing", weight: 1 },
  { key: "communication", label: "Communication", weight: 1 },
];

const MOCK_RESULT: EvaluationResult = {
  scores: {
    originality: 65,
    quality: 86,
    elaboration: 82,
    critical_thinking: 88,
    information_processing: 89,
    communication: 90,
  },
  feedback: "",
  dimensionDetail: {
    originality: {
      score: 65,
      quote:
        "The enrollment data is skewed because part-time students count the same as full-time, so the headcount looks healthier than it really is.",
      badge: "Stage 1 — Enrollment Data · Jordan",
      narrative:
        "You spotted a meaningful framing gap in how enrollment is reported, which shows genuine critical instinct. The insight could have gone further — connecting this to how it affects the budget model would have elevated it from observation to analysis.",
    },
    quality: {
      score: 86,
      quote:
        "If the bond payments are committed costs and can't be cut, then the discretionary budget is actually much smaller than the headline number suggests — closer to $4M than $11M.",
      badge: "Stage 2 — Budget Data · Priya",
      narrative:
        "Solid structural reasoning. You correctly separated committed from discretionary spend and drew a precise implication — that the real margin is narrower than it appears. This is exactly the kind of inference a good analyst makes.",
    },
    elaboration: {
      score: 82,
      quote:
        "I'd want to break the cost-per-student figure by program before presenting anything to leadership, because averaging across all programs hides where the real inefficiencies are.",
      badge: "Stage 3 — Program Data · Marcus",
      narrative:
        "Good instinct for disaggregating data before drawing conclusions. You identified the right unit of analysis and explained why the aggregate masks what matters. The response would be stronger with a proposed next step — what specifically would you look at first?",
    },
    critical_thinking: {
      score: 88,
      quote:
        "The retention rate drop in year two looks alarming, but I'd want to check whether it's driven by a specific cohort or a system-wide shift before calling it a trend.",
      badge: "Stage 2 — Budget Data · Priya",
      narrative:
        "You resisted the temptation to over-conclude from a single data point and identified the right diagnostic question. This is methodologically sound and shows comfort with uncertainty — a key skill for analytical work.",
    },
    information_processing: {
      score: 89,
      quote:
        "So the three signals — flat enrollment, rising fixed costs, and a shrinking discretionary budget — all point in the same direction. The financial cushion is eroding faster than the headline figures show.",
      badge: "Stage 4 — Synthesis · Jordan",
      narrative:
        "Excellent synthesis. You held three separate threads and converged them into a single coherent finding without oversimplifying. This is exactly how a strong analyst presents complex information to a decision-maker.",
    },
    communication: {
      score: 90,
      quote:
        "I'd frame it as: the university isn't in crisis, but it's on a trajectory that becomes a crisis in 3–5 years if enrollment or costs don't shift — and leadership needs to see that now rather than when the options narrow.",
      badge: "Stage 4 — Synthesis · Jordan",
      narrative:
        "Strong executive framing. You gave a clear headline, a time horizon, and a call to action — without being alarmist or vague. This is the kind of communication that makes stakeholders trust an analyst's judgment.",
    },
  },
};

export default function FeedbackPreviewPage() {
  return (
    <FeedbackOverlay
      visible={true}
      result={MOCK_RESULT}
      dimensions={DIMENSIONS}
      subtitle="Ridgeline University — Financial Analyst Simulation"
      onClose={() => {}}
    />
  );
}
