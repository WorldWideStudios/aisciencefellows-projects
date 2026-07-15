import { NextRequest, NextResponse } from "next/server";

export const maxDuration = 30;

const GEMINI_API_KEY = process.env.GEMINI_API_KEY || "";
const GEMINI_MODEL = process.env.GEMINI_MODEL || "gemini-1.5-flash"; // Flash is fast and excellent at audio

export async function POST(req: NextRequest) {
  try {
    if (!GEMINI_API_KEY) {
      return NextResponse.json({ error: "GEMINI_API_KEY not configured" }, { status: 500 });
    }

    const formData = await req.formData();
    const audioFile = formData.get("audio") as File | null;

    if (!audioFile) {
      return NextResponse.json({ error: "audio file is required" }, { status: 400 });
    }

    const audioBytes = Buffer.from(await audioFile.arrayBuffer()).toString("base64");
    const mimeType = audioFile.type || "audio/webm";

    const url = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent?key=${GEMINI_API_KEY}`;
    const payload = {
      contents: [{
        parts: [
          { text: "Provide a precise verbatim transcript of the audio. Do not add any extra text, commentary, or speaker labels. Just the words spoken." },
          { inlineData: { data: audioBytes, mimeType } }
        ]
      }],
      generationConfig: {
        temperature: 0.1 // Low temperature for factual transcription
      }
    };

    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    const data = await res.json();

    if (!res.ok) {
      console.error("Gemini STT error:", JSON.stringify(data));
      return NextResponse.json(
        { error: data.error?.message || "Gemini STT error" },
        { status: res.status }
      );
    }

    const transcript = data.candidates?.[0]?.content?.parts?.[0]?.text?.trim() ?? "";

    return NextResponse.json({ transcript });
  } catch (err) {
    console.error("STT API error:", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "STT error" },
      { status: 500 }
    );
  }
}
