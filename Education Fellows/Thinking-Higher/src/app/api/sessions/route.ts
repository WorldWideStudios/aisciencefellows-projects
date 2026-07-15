import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import type { Session, SurveyResponse, ProfileData, TaskResult } from "@/lib/types";

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { action } = body;

  if (action === "createSession") {
    const { participantId, scenarioId, metadata } = body;
    const authSession = await auth();
    const session: Session = {
      id: generateId(),
      participantId: participantId || metadata?.participantId || generateId(),
      scenarioId,
      startedAt: Date.now(),
      completedAt: null,
      status: "active",
      metadata: metadata || null,
      userEmail: authSession?.user?.email ?? null,
      userName: authSession?.user?.name ?? null,
    };
    await db.saveSession(session);
    return NextResponse.json({ session });
  }

  if (action === "saveTranscript") {
    const { sessionId, stageId, entries } = body;
    await db.saveTranscript(sessionId, stageId, entries);
    return NextResponse.json({ ok: true });
  }

  if (action === "saveAssessment") {
    const { sessionId, scores, feedback, stageEvals, responseTimesMs } = body as {
      sessionId: string;
      scores: Record<string, number>;
      feedback: string;
      stageEvals: import("@/lib/types").StageEvalResult[];
      responseTimesMs: number[];
    };
    await db.saveAssessment(sessionId, scores, feedback, stageEvals ?? [], responseTimesMs);
    await db.updateSession(sessionId, {
      status: "completed",
      completedAt: Date.now(),
    });
    return NextResponse.json({ ok: true });
  }

  if (action === "saveSurvey") {
    const { sessionId, stageId, responses } = body as {
      sessionId: string;
      stageId: string;
      responses: SurveyResponse[];
    };
    await db.saveSurvey(sessionId, stageId, responses);
    return NextResponse.json({ ok: true });
  }

  if (action === "saveParticipantProfile") {
    const { sessionId, profile } = body as {
      sessionId: string;
      profile: ProfileData;
    };
    await db.saveParticipantProfile(sessionId, profile);
    return NextResponse.json({ ok: true });
  }

  if (action === "saveTaskResult") {
    const { result } = body as { result: TaskResult };
    await db.saveTaskResult(result);
    return NextResponse.json({ ok: true });
  }

  if (action === "getTaskResult") {
    const { sessionId, stageId } = body;
    const result = await db.getTaskResult(sessionId, stageId);
    return NextResponse.json({ result });
  }

  return NextResponse.json({ error: "Unknown action" }, { status: 400 });
}

export async function GET(req: NextRequest) {
  const sessionId = req.nextUrl.searchParams.get("sessionId");
  if (!sessionId) {
    return NextResponse.json({ error: "sessionId required" }, { status: 400 });
  }

  const session = await db.getSession(sessionId);
  if (!session) {
    return NextResponse.json({ error: "Session not found" }, { status: 404 });
  }

  const assessment = await db.getAssessment(sessionId);
  return NextResponse.json({ session, assessment });
}
