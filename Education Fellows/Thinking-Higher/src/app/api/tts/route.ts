import { NextRequest, NextResponse } from "next/server";
import { PollyClient, SynthesizeSpeechCommand, Engine, OutputFormat, TextType } from "@aws-sdk/client-polly";

export const maxDuration = 30;

const polly = new PollyClient({
  region: process.env.AWS_REGION || "us-east-1",
  credentials: {
    accessKeyId: process.env.AWS_ACCESS_KEY_ID || "",
    secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY || "",
  },
});

const VALID_VOICES = new Set([
  "Joanna", "Ruth", "Matthew", "Stephen", "Amy", "Brian",
  "Emma", "Ivy", "Kendra", "Kimberly", "Salli", "Joey",
  "Justin", "Kevin", "Daniyar", "Hiujin", "Lupe", "Pedro",
]);

export async function POST(req: NextRequest) {
  try {
    if (!process.env.AWS_ACCESS_KEY_ID || !process.env.AWS_SECRET_ACCESS_KEY) {
      return NextResponse.json({ error: "AWS credentials not configured" }, { status: 500 });
    }

    const { text, voiceId = "Joanna" } = await req.json();

    if (!text || typeof text !== "string") {
      return NextResponse.json({ error: "text is required" }, { status: 400 });
    }

    const safeVoiceId = VALID_VOICES.has(voiceId) ? voiceId : "Joanna";

    const command = new SynthesizeSpeechCommand({
      Text: text.slice(0, 3000),
      VoiceId: safeVoiceId as never,
      Engine: Engine.NEURAL,
      OutputFormat: OutputFormat.MP3,
      TextType: TextType.TEXT,
    });

    const response = await polly.send(command);

    if (!response.AudioStream) {
      return NextResponse.json({ error: "Polly returned no audio" }, { status: 502 });
    }

    const chunks: Uint8Array[] = [];
    for await (const chunk of response.AudioStream as AsyncIterable<Uint8Array>) {
      chunks.push(chunk);
    }
    const audioBuffer = Buffer.concat(chunks);

    return new NextResponse(audioBuffer, {
      status: 200,
      headers: {
        "Content-Type": "audio/mpeg",
        "Content-Length": audioBuffer.length.toString(),
        "Cache-Control": "no-store",
      },
    });
  } catch (err) {
    console.error("TTS API error:", err);
    return NextResponse.json(
      { error: err instanceof Error ? err.message : "TTS error" },
      { status: 500 }
    );
  }
}
