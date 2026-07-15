import { NextRequest, NextResponse } from "next/server";
import { ProbeClassification } from "@/lib/types";

export const maxDuration = 30;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-2.5-flash";

const VALID_CLASSIFICATIONS: ProbeClassification[] = ["strong", "vague", "conflates", "off-topic"];

export async function POST(req: NextRequest) {
  if (!GEMINI_API_KEY) {
    return NextResponse.json({ error: "GEMINI_API_KEY not configured" }, { status: 500 });
  }

  const { studentText, evaluatorPrompt } = await req.json();
  if (!studentText || !evaluatorPrompt) {
    return NextResponse.json({ error: "Missing studentText or evaluatorPrompt" }, { status: 400 });
  }

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;

  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: evaluatorPrompt }] },
      contents: [{ role: "user", parts: [{ text: studentText }] }],
      generationConfig: { maxOutputTokens: 10, temperature: 0 },
    }),
  });

  const data = await res.json();
  const raw = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim().toLowerCase() ?? "";

  // Sanitise — strip punctuation, take first word
  const token = raw.replace(/[^a-z-]/g, "").split(" ")[0] as ProbeClassification;
  const classification: ProbeClassification = VALID_CLASSIFICATIONS.includes(token) ? token : "vague";

  return NextResponse.json({ classification });
}
