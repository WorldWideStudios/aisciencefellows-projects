/**
 * Ridgeline Evaluation Pipeline Test
 *
 * Runs the full per-stage evaluation pipeline against pre-scripted student
 * transcripts, printing every intermediate artifact:
 *   • Stage transcript (input)
 *   • System prompt sent to the LLM
 *   • Raw LLM response (unparsed JSON string)
 *   • Parsed DimensionEval matrix
 *
 * Then aggregates across stages and runs the feedback synthesis call.
 *
 * Usage:
 *   npx tsx scripts/test-ridgeline-eval.ts
 */

import { readFileSync } from "fs";
import { resolve } from "path";

// ── Load .env.local ────────────────────────────────────────────────────────────

try {
  const envPath = resolve(process.cwd(), ".env.local");
  const envContent = readFileSync(envPath, "utf8");
  for (const line of envContent.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx === -1) continue;
    const key = trimmed.slice(0, eqIdx).trim();
    const value = trimmed.slice(eqIdx + 1).trim().replace(/^["']|["']$/g, "");
    if (key && !process.env[key]) process.env[key] = value;
  }
} catch {
  console.warn("No .env.local found — using existing environment variables.");
}

const GEMINI_API_KEY = process.env.GEMINI_API_KEY ?? "";
const GEMINI_MODEL = process.env.GEMINI_MODEL ?? "gemini-2.5-flash";

if (!GEMINI_API_KEY) {
  console.error("ERROR: GEMINI_API_KEY not set.");
  process.exit(1);
}

// ── Types ──────────────────────────────────────────────────────────────────────

interface DimensionEval {
  score: number;
  evidence: string;
  confidence: number;
}

interface StageEvalResult {
  stageId: string;
  badge: string;
  agentName: string;
  dimensions: Record<string, DimensionEval>;
}

interface StageTranscriptData {
  stageId: string;
  badge: string;
  agentName: string;
  assessmentRubric: string;
  transcript: string;
}

interface SkillDimension {
  key: string;
  label: string;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const DIMENSION_KEYS = [
  "originality", "quality", "elaboration",
  "critical_thinking", "information_processing", "communication",
];

const SKILL_DIMENSIONS: SkillDimension[] = [
  { key: "originality",           label: "Originality" },
  { key: "quality",               label: "Quality" },
  { key: "elaboration",           label: "Elaboration" },
  { key: "critical_thinking",     label: "Analytical Thinking" },
  { key: "information_processing",label: "Information Processing" },
  { key: "communication",         label: "Communication" },
];

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

// ── Pre-scripted student transcripts ──────────────────────────────────────────
//
// Each transcript uses the format:
//   Student: "..."
//   Agent: "..."
//
// These represent a competent but not perfect student performance.

const STAGE_SCRIPTS: StageTranscriptData[] = [
  {
    stageId: "kickoff",
    badge: "Stage 1 — Kick-Off",
    agentName: "Jordan",
    assessmentRubric:
      "Assess whether the student asks questions that clarify the scope of their assignment, the constraints they must work within, and their role versus Priya and Derek's roles.",
    transcript: `Student: "Thanks for setting this up. Before I meet with Priya and Derek, I want to make sure I understand my role correctly — am I expected to summarize what they tell me, or is my job to form my own interpretation and bring a recommendation?"
Agent: "Your job is to analyze. Priya and Derek give you data. What it means — that's on you."
Student: "Got it. On constraints — you mentioned the board has specific guardrails. Can you spell those out so I know what's off the table before I start?"
Agent: "Back in surplus within two fiscal years. Reserves stay above three million. Those aren't targets — they're hard limits."
Student: "Is there any prior analysis I should be aware of, or are we starting from scratch?"
Agent: "Fresh eyes. That's why you're here. Priya connects with you first, then Derek. Let's get moving."`,
  },

  {
    stageId: "finance",
    badge: "Stage 2 — Budget Data",
    agentName: "Priya",
    assessmentRubric:
      "Assess whether the student identifies the key budget drivers — particularly the Facilities & Operations spike (36.9% increase) and its source (bond payments), and whether they connect State Appropriations decline to the structural revenue problem.",
    transcript: `Student: "Total revenue dropped from $39.2 million to $34.9 million over three years — that's about a $4.3 million decline. Which lines are driving most of that?"
Agent: "State appropriations dropped the most in absolute terms — from $18.2 million to $15.9 million. Tuition and fees also declined, from $12.65 million to $11 million."
Student: "Facilities and Operations jumped from $5.8 million to $7.9 million — that's a $2.1 million increase in two years. What's behind that?"
Agent: "Renovation bond payments began in FY2023. Before that, Facilities was more stable. The bond payments are the main driver."
Student: "Are those bond payments fixed or variable — is there any room to renegotiate the schedule?"
Agent: "Fixed. They're a committed obligation set by the bond terms."
Student: "So the expenditure side has a locked-in cost driver that isn't going away. What about the Instruction line — it dipped slightly. Is that from fewer faculty or something else?"
Agent: "It declined about $500K over the period. The breakdown is an HR question — I can't speak to that."
Student: "Last check: the net position went from a $2.1 million surplus in FY2022 to a $4 million deficit in FY2024?"
Agent: "Correct. That's everything I can speak to from the data side. Good luck with the analysis."`,
  },

  {
    stageId: "enrollment",
    badge: "Stage 3 — Enrollment Data",
    agentName: "Derek",
    assessmentRubric:
      "Assess whether the student identifies the Health Sciences capacity ceiling (the footnote is the critical thinking test of this stage) and understands the asymmetric impact of Liberal Arts decline on overall revenue.",
    transcript: `Student: "Total credit headcount dropped from 6,490 to 5,840 — about 10% over three years. Is the decline spread evenly or concentrated in specific programs?"
Agent: "It's concentrated. Liberal Arts saw the sharpest decline — down 430 students. Business, IT, and Trades all declined more modestly. Health Sciences actually grew."
Student: "Health Sciences grew — by how much, and is there a ceiling on how much it can expand?"
Agent: "Up about 60 students, to 1,050. There is a ceiling — we're at roughly 94% of the maximum permitted under state nursing board clinical faculty ratio requirements. Any material increase would require at least two additional clinical faculty, which isn't in the current budget."
Student: "So Health Sciences can't absorb the enrollment loss from Liberal Arts without upfront faculty investment that isn't currently funded. What's the full-time versus part-time breakdown for the Liberal Arts decline?"
Agent: "Full-time went from 1,840 to 1,560, and part-time from 980 to 830. The full-time decline is larger in absolute terms."
Student: "Full-time students pay more tuition per head, so their decline has an outsized drag on the revenue line — the Liberal Arts loss is hitting revenue harder than the raw headcount suggests."
Agent: "That's right — full-time is 12 or more credits. They generate more tuition revenue than part-time."
Student: "That's the picture I needed. Thank you."`,
  },

  {
    stageId: "presentation",
    badge: "Stage 4 — Presentation",
    agentName: "Jordan",
    assessmentRubric:
      "Assess whether the student delivers a clear, evidence-based analysis that names all three structural headwinds (enrollment decline → tuition revenue loss, declining state appropriations, rising committed facilities costs), stays within the board's constraints (no tuition increases, reserves above $3M, surplus by FY2026), and makes a specific recommendation with at least one named risk or failure scenario.",
    transcript: `Student: "The college is facing three structural headwinds that together explain the swing from a $2.1 million surplus in FY2022 to a $4 million deficit in FY2024. First: enrollment decline. Credit headcount dropped 10%, concentrated in Liberal Arts — down 430 students. Because Liberal Arts is the largest program and those are mostly full-time students, this has an outsized drag on tuition revenue. Second: state appropriations declined $2.4 million. I'd treat that as structural — not a one-time correction. Third: Facilities and Operations costs jumped $2.1 million, driven entirely by renovation bond payments that started in FY2023. Those are committed costs — not discretionary."
Agent: "Good. Health Sciences is growing. Why doesn't that offset the Liberal Arts decline?"
Student: "Health Sciences gained 60 students against a Liberal Arts loss of 430. Even setting aside the volume mismatch, Health Sciences is at 94% of licensed clinical capacity — any meaningful expansion requires at least two additional clinical faculty that aren't budgeted. It can't serve as a growth engine without upfront investment."
Agent: "Is the state appropriations decline a Ridgeline-specific problem or something broader?"
Student: "I'd treat it as structural and regional. The three-year trend is consistent, and community college funding has broadly been under pressure. I wouldn't plan around a reversal."
Agent: "Given all that — what do you recommend?"
Student: "The bond payments are locked in, so we can't close the deficit primarily through cost-cutting. Instruction is the only remaining expenditure lever at scale, but cutting there risks accelerating enrollment decline — which makes the problem worse. My recommendation is to focus on demand-side recovery: targeted investment in programs with growth potential outside the clinical capacity constraint, and retention initiatives for the Liberal Arts population that's leaving. Combined with holding admin costs flat, this is the most feasible path to surplus by FY2026. The main risk is that demand-side interventions take time — if enrollment doesn't stabilize in FY2025, the FY2026 target becomes very difficult to hit."
Agent: "The bond payment accelerates by about $400K in FY2026. Factor that in."
Student: "That makes the sequencing more urgent. We need to see revenue improvement in FY2025, not just stabilization — enrollment initiatives need to start immediately rather than in the second year of the plan."
Agent: "I'll take this into the room. Nice work."`,
  },
];

// ── Gemini caller ──────────────────────────────────────────────────────────────

async function callGemini(system: string, userMessage: string, maxTokens = 4096): Promise<string> {
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;
  const payload = {
    systemInstruction: { parts: [{ text: system }] },
    contents: [{ role: "user", parts: [{ text: userMessage }] }],
    generationConfig: {
      maxOutputTokens: maxTokens,
      thinkingConfig: { thinkingBudget: 0 },  // disable thinking tokens; all budget goes to output
    },
  };

  let lastErr: unknown;
  for (let attempt = 0; attempt < 5; attempt++) {
    if (attempt > 0) {
      const delayMs = 2000 * 2 ** (attempt - 1);  // 2s, 4s, 8s, 16s
      console.log(`  [Retry ${attempt}/4 in ${delayMs / 1000}s...]`);
      await new Promise(r => setTimeout(r, delayMs));
    }
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data: Record<string, unknown> = await res.json() as Record<string, unknown>;
    if (!res.ok) {
      lastErr = data;
      continue;
    }
    const candidates = data.candidates as Array<{ content: { parts: Array<{ text: string }> } }> | undefined;
    const text = candidates?.[0]?.content?.parts?.[0]?.text;
    if (!text) throw new Error("Gemini returned no text");
    return text;
  }
  throw new Error(`Gemini failed after 3 attempts: ${JSON.stringify(lastErr)}`);
}

// ── Formatting helpers ─────────────────────────────────────────────────────────

const SEP  = "═".repeat(72);
const SEP2 = "─".repeat(72);

function header(text: string) {
  console.log(`\n${SEP}`);
  console.log(`  ${text}`);
  console.log(SEP);
}

function sub(text: string) {
  console.log(`\n${SEP2}`);
  console.log(`  ${text}`);
  console.log(SEP2);
}

function printMatrix(result: StageEvalResult) {
  console.log("\n  DIMENSION MATRIX:");
  console.log(`  ${"Dimension".padEnd(26)} ${"Score".padStart(5)}  ${"Conf".padStart(4)}  Evidence`);
  console.log("  " + "─".repeat(68));
  for (const key of DIMENSION_KEYS) {
    const d = result.dimensions[key];
    if (!d) continue;
    const dim = SKILL_DIMENSIONS.find(s => s.key === key)?.label ?? key;
    const evidence = d.evidence.length > 40 ? d.evidence.slice(0, 37) + "..." : d.evidence;
    console.log(
      `  ${dim.padEnd(26)} ${String(d.score).padStart(5)}  ${String(d.confidence).padStart(4)}  "${evidence}"`
    );
  }
}

// ── Per-stage eval ─────────────────────────────────────────────────────────────

async function runStageEval(stage: StageTranscriptData, index: number): Promise<StageEvalResult | null> {
  header(`STAGE ${index + 1}: ${stage.badge}  (Agent: ${stage.agentName})`);

  // 1. Print transcript
  sub("INPUT — Student transcript");
  for (const line of stage.transcript.split("\n")) {
    console.log("  " + line);
  }

  // 2. Build system prompt
  const systemPrompt = `You are evaluating a student's performance in one stage of a workplace simulation.

Stage: ${stage.badge}
Agent: ${stage.agentName}
Assessment focus: ${stage.assessmentRubric}

${STAGE_EVAL_INSTRUCTIONS}`;

  sub("SYSTEM PROMPT sent to LLM");
  for (const line of systemPrompt.split("\n")) {
    console.log("  " + line);
  }

  const userMessage = `Student transcript for this stage:\n\n${stage.transcript}`;

  // 3. Call LLM
  console.log("\n  [Calling Gemini...]\n");
  let rawResponse: string;
  try {
    rawResponse = await callGemini(systemPrompt, userMessage, 700);
  } catch (err) {
    console.error("  LLM call failed:", err);
    return null;
  }

  // 4. Print raw response
  sub("RAW LLM RESPONSE");
  console.log("  " + rawResponse);

  // 5. Parse
  let parsed: Record<string, { score: number; evidence: string; confidence: number }>;
  try {
    const clean = rawResponse.replace(/```json|```/g, "").trim();
    parsed = JSON.parse(clean);
  } catch (err) {
    console.error("  Parse failed:", err);
    return null;
  }

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

  const result: StageEvalResult = {
    stageId: stage.stageId,
    badge: stage.badge,
    agentName: stage.agentName,
    dimensions,
  };

  // 6. Print parsed matrix
  sub("PARSED EVALUATION MATRIX");
  printMatrix(result);

  return result;
}

// ── Aggregation ────────────────────────────────────────────────────────────────

function aggregate(stageEvals: StageEvalResult[]): {
  scores: Record<string, number>;
  bestEvidence: Record<string, { quote: string; badge: string; confidence: number }>;
} {
  const scores: Record<string, number> = {};
  const bestEvidence: Record<string, { quote: string; badge: string; confidence: number }> = {};

  for (const dim of SKILL_DIMENSIONS) {
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
    const best = (withEvidence.length > 0 ? withEvidence : entries)
      .sort((a, b) => b.confidence - a.confidence)[0];
    bestEvidence[dim.key] = {
      quote: best.evidence ?? "",
      badge: best.badge,
      confidence: best.confidence,
    };
  }

  return { scores, bestEvidence };
}

// ── Feedback synthesis ─────────────────────────────────────────────────────────

async function runFeedbackSynthesis(
  scores: Record<string, number>,
  bestEvidence: Record<string, { quote: string; badge: string; confidence: number }>
): Promise<void> {
  header("FEEDBACK SYNTHESIS (final LLM call)");

  const evidenceLines = SKILL_DIMENSIONS.map(d => {
    const ev = bestEvidence[d.key];
    const quote = ev?.quote ? `"${ev.quote}" [${ev.badge}]` : "(no direct quote available)";
    return `- ${d.label} (${scores[d.key]}/100): ${quote}`;
  }).join("\n");

  const userMessage = `Dimension scores and evidence:\n${evidenceLines}`;

  sub("SYSTEM PROMPT sent to LLM");
  for (const line of FEEDBACK_INSTRUCTIONS.split("\n")) console.log("  " + line);
  sub("USER MESSAGE sent to LLM");
  for (const line of userMessage.split("\n")) console.log("  " + line);

  console.log("\n  [Calling Gemini...]\n");
  let rawResponse: string;
  try {
    rawResponse = await callGemini(FEEDBACK_INSTRUCTIONS, userMessage, 1200);
  } catch (err) {
    console.error("  LLM call failed:", err);
    return;
  }

  sub("RAW LLM RESPONSE");
  console.log("  " + rawResponse);

  let narratives: Record<string, string>;
  try {
    const clean = rawResponse.replace(/```json|```/g, "").trim();
    narratives = JSON.parse(clean);
  } catch (err) {
    console.error("  Parse failed:", err);
    return;
  }

  sub("PARSED NARRATIVES");
  for (const dim of SKILL_DIMENSIONS) {
    console.log(`\n  [${dim.label}]`);
    console.log(`  ${narratives[dim.key] ?? "(missing)"}`);
  }
}

// ── Main ───────────────────────────────────────────────────────────────────────

async function main() {
  console.log(`\n${"█".repeat(72)}`);
  console.log("  RIDGELINE EVALUATION PIPELINE TEST");
  console.log(`  Model: ${GEMINI_MODEL}`);
  console.log(`  Stages: ${STAGE_SCRIPTS.length}`);
  console.log(`${"█".repeat(72)}`);

  const stageEvals: StageEvalResult[] = [];

  for (let i = 0; i < STAGE_SCRIPTS.length; i++) {
    if (i > 0) await new Promise(r => setTimeout(r, 3000));  // avoid rate-limit bursting
    const result = await runStageEval(STAGE_SCRIPTS[i], i);
    if (result) stageEvals.push(result);
  }

  // Aggregation summary
  header("AGGREGATION — Confidence-Weighted Scores");

  if (stageEvals.length === 0) {
    console.log("  No successful stage evals to aggregate.");
    return;
  }

  const { scores, bestEvidence } = aggregate(stageEvals);

  console.log("\n  FULL MATRIX (all stages × all dimensions):\n");
  const colW = 14;
  const dimW = 26;
  const stageHeaders = stageEvals.map(s => s.badge.replace("Stage ", "S").slice(0, colW));
  console.log("  " + "Dimension".padEnd(dimW) + stageHeaders.map(h => h.padStart(colW)).join("") + "  WEIGHTED");
  console.log("  " + "─".repeat(dimW + colW * stageEvals.length + 10));

  for (const dim of SKILL_DIMENSIONS) {
    const stageCols = stageEvals.map(s => {
      const d = s.dimensions[dim.key];
      return d ? `${d.score}(c${d.confidence})` : "—";
    });
    const weightedStr = String(scores[dim.key]).padStart(8);
    console.log(
      "  " + dim.label.padEnd(dimW) +
      stageCols.map(c => c.padStart(colW)).join("") +
      weightedStr
    );
  }

  console.log("\n  BEST EVIDENCE per dimension:");
  console.log("  " + "─".repeat(70));
  for (const dim of SKILL_DIMENSIONS) {
    const ev = bestEvidence[dim.key];
    const shortQuote = ev.quote.length > 60 ? ev.quote.slice(0, 57) + "..." : ev.quote;
    console.log(`  ${dim.label.padEnd(26)} [${ev.badge ?? "—"}]`);
    console.log(`    "${shortQuote}"`);
  }

  await runFeedbackSynthesis(scores, bestEvidence);

  header("TEST COMPLETE");
  console.log(`  ${stageEvals.length}/${STAGE_SCRIPTS.length} stage evals succeeded.\n`);
}

main().catch(err => {
  console.error("Fatal error:", err);
  process.exit(1);
});
