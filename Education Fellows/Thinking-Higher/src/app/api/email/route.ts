import { NextRequest, NextResponse } from "next/server";
import { sendSessionReport } from "@/lib/email/send-report";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const { to, sessionId, taskType, summary, scores, modelFit, participantName } = body;

  if (!to || !sessionId) {
    return NextResponse.json({ error: "to and sessionId required" }, { status: 400 });
  }

  const result = await sendSessionReport({
    to,
    sessionId,
    taskType,
    summary,
    scores,
    modelFit,
    participantName,
  });

  return NextResponse.json({ ok: true, result });
}
