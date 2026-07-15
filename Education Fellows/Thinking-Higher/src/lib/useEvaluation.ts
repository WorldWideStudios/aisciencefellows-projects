"use client";

import { useState, useCallback } from "react";
import { callLLM } from "./llm";
import { EvaluationResult, StageEvalResult, DimensionEval, SkillDimension } from "./types";

export interface StageTranscriptData {
  stageId: string;
  badge: string;
  agentName: string;
  assessmentRubric: string;
  transcript: string;
}

interface UseEvaluationOptions {
  skillDimensions: SkillDimension[];
  onComplete?: (result: EvaluationResult) => void;
}

const DIMENSION_KEYS = ["originality", "quality", "elaboration", "critical_thinking", "information_processing", "communication"];

const STAGE_EVAL_INSTRUCTIONS = `Score the student on 6 dimensions (0–100 each). For each dimension:
- "score": how well the student performed (0–100)
- "evidence": the single most relevant student message as a direct quote. Rules: preserve complete sentences only. You may use "..." between whole sentences to bridge two relevant parts, but never truncate within a sentence. Use "" if the student said nothing relevant to this dimension in this stage.
- "confidence": your confidence in this score (0–100; use low values when the student had little opportunity to demonstrate this dimension in this stage)

Return ONLY valid JSON with no markdown fences:
{"originality":{"score":N,"evidence":"...","confidence":N},"quality":{"score":N,"evidence":"...","confidence":N},"elaboration":{"score":N,"evidence":"...","confidence":N},"critical_thinking":{"score":N,"evidence":"...","confidence":N},"information_processing":{"score":N,"evidence":"...","confidence":N},"communication":{"score":N,"evidence":"...","confidence":N}}`;

const FEEDBACK_INSTRUCTIONS = `You are writing structured evaluator feedback for a student who completed a workplace simulation.
For each dimension, write 1–2 sentences of specific, direct commentary. Reference the evidence quote naturally — do not just restate it.
Return ONLY valid JSON with no markdown fences:
{"originality":"...","quality":"...","elaboration":"...","critical_thinking":"...","information_processing":"...","communication":"..."}`;

async function callStageEval(stage: StageTranscriptData): Promise<StageEvalResult | null> {
  const system = `You are evaluating a student's performance in one stage of a workplace simulation.

Stage: ${stage.badge}
Agent: ${stage.agentName}
Assessment focus: ${stage.assessmentRubric}

${STAGE_EVAL_INSTRUCTIONS}`;

  try {
    const raw = await callLLM({
      system,
      messages: [{ role: "user", content: `Student transcript for this stage:\n\n${stage.transcript}` }],
      maxTokens: 1200,
      disableThinking: true,
    });
    const clean = raw.replace(/```json|```/g, "").trim();
    const parsed = JSON.parse(clean);
    const dimensions: Record<string, DimensionEval> = {};
    for (const key of DIMENSION_KEYS) {
      if (parsed[key]) {
        dimensions[key] = {
          score: Number(parsed[key].score) || 50,
          evidence: String(parsed[key].evidence ?? ""),
          confidence: Number(parsed[key].confidence) || 50,
        };
      }
    }
    return { stageId: stage.stageId, badge: stage.badge, agentName: stage.agentName, dimensions };
  } catch {
    return null;
  }
}

function aggregate(
  stageEvals: StageEvalResult[],
  dimensions: SkillDimension[]
): {
  scores: Record<string, number>;
  bestEvidence: Record<string, { quote: string; badge: string; confidence: number }>;
} {
  const scores: Record<string, number> = {};
  const bestEvidence: Record<string, { quote: string; badge: string; confidence: number }> = {};

  for (const dim of dimensions) {
    const entries = stageEvals
      .map(s => ({ ...s.dimensions[dim.key], badge: s.badge }))
      .filter(e => e && e.confidence !== undefined);

    if (entries.length === 0) {
      scores[dim.key] = 70;
      bestEvidence[dim.key] = { quote: "", badge: "", confidence: 0 };
      continue;
    }

    const totalConf = entries.reduce((s, e) => s + e.confidence, 0);
    scores[dim.key] = totalConf > 0
      ? Math.round(entries.reduce((s, e) => s + e.score * e.confidence, 0) / totalConf)
      : Math.round(entries.reduce((s, e) => s + e.score, 0) / entries.length);

    const withEvidence = entries.filter(e => e.evidence && e.evidence.trim() !== "");
    const best = withEvidence.sort((a, b) => b.confidence - a.confidence)[0]
      ?? entries.sort((a, b) => b.confidence - a.confidence)[0];
    bestEvidence[dim.key] = { quote: best.evidence ?? "", badge: best.badge, confidence: best.confidence };
  }

  return { scores, bestEvidence };
}

async function callFeedbackSynthesis(
  scores: Record<string, number>,
  bestEvidence: Record<string, { quote: string; badge: string; confidence: number }>,
  dimensions: SkillDimension[]
): Promise<Record<string, string>> {
  const evidenceLines = dimensions.map(d => {
    const ev = bestEvidence[d.key];
    const quote = ev?.quote ? `"${ev.quote}" [${ev.badge}]` : "(no direct quote available)";
    return `- ${d.label} (${scores[d.key]}/100): ${quote}`;
  }).join("\n");

  try {
    const raw = await callLLM({
      system: FEEDBACK_INSTRUCTIONS,
      messages: [{ role: "user", content: `Dimension scores and evidence:\n${evidenceLines}` }],
      maxTokens: 1200,
      disableThinking: true,
    });
    const clean = raw.replace(/```json|```/g, "").trim();
    return JSON.parse(clean);
  } catch {
    const fallback: Record<string, string> = {};
    for (const d of dimensions) fallback[d.key] = "";
    return fallback;
  }
}

async function apiSaveAssessment(
  sessionId: string,
  result: EvaluationResult,
  stageEvals: StageEvalResult[],
  responseTimesMs: number[]
) {
  await fetch("/api/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      action: "saveAssessment",
      sessionId,
      scores: result.scores,
      feedback: result.feedback,
      stageEvals,
      responseTimesMs,
    }),
  });
}

function buildFallback(dimensions: SkillDimension[]): EvaluationResult {
  const scores: Record<string, number> = {};
  for (const d of dimensions) scores[d.key] = 70;
  return { scores, feedback: "You completed all stages of the simulation. Review the facilitator key for detailed rubric guidance." };
}

export function useEvaluation({ skillDimensions, onComplete }: UseEvaluationOptions) {
  const [result, setResult] = useState<EvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);

  const trigger = useCallback(async (
    stages: StageTranscriptData[],
    options: { sessionId?: string | null; responseTimesMs?: number[] } = {}
  ) => {
    const { sessionId, responseTimesMs = [] } = options;
    setLoading(true);

    try {
      const rawEvals = await Promise.all(stages.map(s => callStageEval(s)));
      const stageEvals = rawEvals.filter((e): e is StageEvalResult => e !== null);

      if (stageEvals.length === 0) {
        const fallback = buildFallback(skillDimensions);
        setResult(fallback);
        onComplete?.(fallback);
        if (sessionId) apiSaveAssessment(sessionId, fallback, [], responseTimesMs).catch(() => {});
        return;
      }

      const { scores, bestEvidence } = aggregate(stageEvals, skillDimensions);
      const narratives = await callFeedbackSynthesis(scores, bestEvidence, skillDimensions);

      const dimensionDetail: EvaluationResult["dimensionDetail"] = {};
      for (const d of skillDimensions) {
        dimensionDetail[d.key] = {
          score: scores[d.key],
          quote: bestEvidence[d.key]?.quote ?? "",
          badge: bestEvidence[d.key]?.badge ?? "",
          narrative: narratives[d.key] ?? "",
        };
      }

      const evalResult: EvaluationResult = { scores, feedback: "", dimensionDetail };
      setResult(evalResult);
      onComplete?.(evalResult);
      if (sessionId) {
        apiSaveAssessment(sessionId, evalResult, stageEvals, responseTimesMs).catch(() => {});
      }
    } catch {
      const fallback = buildFallback(skillDimensions);
      setResult(fallback);
      onComplete?.(fallback);
      if (sessionId) apiSaveAssessment(sessionId, fallback, [], responseTimesMs).catch(() => {});
    } finally {
      setLoading(false);
    }
  }, [skillDimensions, onComplete]);

  return { result, loading, trigger };
}
