import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { computeStageMetrics, computeCognitiveSignals } from "@/lib/rt-metrics";
import { runGeCCoPipeline } from "@/lib/gecco";
import { predictWithCentaur, formatForCentaur, classifyResponseStrategy } from "@/lib/centaur";
import type { TranscriptEntry } from "@/lib/types";

// POST: Compute cognitive profile for a completed session
export async function POST(req: NextRequest) {
  const { sessionId } = await req.json();

  const session = await db.getSession(sessionId);
  if (!session) {
    return NextResponse.json({ error: "Session not found" }, { status: 404 });
  }

  // Collect all stage transcripts
  const stageIds = ["marcus", "alex", "sarah"];
  const allEntries: Record<string, TranscriptEntry[]> = {};

  for (const stageId of stageIds) {
    const transcript = await db.getTranscript(sessionId, stageId);
    allEntries[stageId] = transcript?.entries ?? [];
  }

  // Compute RT metrics per stage
  const stageMetrics = stageIds.map((id) => computeStageMetrics(id, allEntries[id]));

  // Compute cross-stage cognitive signals
  const signals = computeCognitiveSignals(stageMetrics, allEntries);

  // Run Centaur predictions if configured (non-blocking)
  let centaurResults = null;
  const centaurEndpoint = process.env.CENTAUR_ENDPOINT;
  if (centaurEndpoint) {
    const predictions: Record<string, unknown> = {};
    for (const stageId of stageIds) {
      const userMsgs = allEntries[stageId].filter((e) => e.role === "user");
      for (const msg of userMsgs) {
        const strategy = classifyResponseStrategy(msg.content, stageId);
        const prompt = formatForCentaur(stageId, "", msg.content, [
          "deep-probe",
          "clarifying-question",
          "proactive-ownership",
          "brief-acknowledgment",
          "substantive-response",
        ]);
        const pred = await predictWithCentaur(prompt);
        if (pred) {
          predictions[`${stageId}:${strategy}`] = pred;
        }
      }
    }
    centaurResults = predictions;
  }

  // Run GeCCo model generation if enough data
  let geccoModel = null;
  if (signals.allUserRTs.length >= 3) {
    geccoModel = await runGeCCoPipeline(
      "Workplace simulation with 3 stages: requirements gathering (UX designer), bug report discussion (tech lead), timeline negotiation (project manager). Measures analytical thinking, communication, ownership, and adaptability.",
      signals
    );
  }

  // Save profile to DB
  const profile = {
    sessionId,
    signals,
    centaurResults,
    geccoModel,
    computedAt: Date.now(),
  };
  await db.saveProfile(sessionId, profile);

  return NextResponse.json({ profile });
}

// GET: Retrieve existing profile
export async function GET(req: NextRequest) {
  const sessionId = req.nextUrl.searchParams.get("sessionId");
  if (!sessionId) {
    return NextResponse.json({ error: "sessionId required" }, { status: 400 });
  }

  const profile = await db.getProfile(sessionId);
  if (!profile) {
    return NextResponse.json({ error: "Profile not found" }, { status: 404 });
  }

  return NextResponse.json({ profile });
}
