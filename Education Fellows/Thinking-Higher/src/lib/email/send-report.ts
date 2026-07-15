import { Resend } from "resend";
import SessionReport from "./templates/session-report";

let _resend: Resend | null = null;
function getResend(): Resend | null {
  if (!process.env.RESEND_API_KEY) return null;
  if (!_resend) _resend = new Resend(process.env.RESEND_API_KEY);
  return _resend;
}

export async function sendSessionReport(params: {
  to: string;
  sessionId: string;
  taskType: string;
  summary: {
    totalTrials: number;
    completedTrials: number;
    meanRT: number;
    accuracy?: number;
  };
  scores?: {
    analytical?: number;
    communication?: number;
    ownership?: number;
    adaptability?: number;
  };
  modelFit?: {
    alpha?: number;
    tau?: number;
  };
  participantName?: string;
}) {
  const resend = getResend();
  if (!resend) {
    console.log("RESEND_API_KEY not set, skipping email");
    return null;
  }

  const { data, error } = await resend.emails.send({
    from: "ThinkHigher <reports@thinkhigher.vercel.app>",
    to: params.to,
    subject: `Your ThinkHigher Cognitive Profile — ${params.taskType}`,
    react: SessionReport({
      sessionId: params.sessionId,
      completedAt: new Date().toLocaleDateString(),
      taskType: params.taskType,
      summary: params.summary,
      scores: params.scores,
      modelFit: params.modelFit,
      participantName: params.participantName,
    }),
  });

  if (error) {
    console.error("Email send failed:", error);
    return null;
  }
  return data;
}
