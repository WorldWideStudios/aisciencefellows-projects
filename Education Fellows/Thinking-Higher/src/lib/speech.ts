// Splits text into sentences for progressive TTS delivery
export function chunkBySentence(text: string): string[] {
  const raw = text.match(/[^.!?]+[.!?]+["']?|[^.!?]+$/g) ?? [text];
  return raw.map((s) => s.trim()).filter((s) => s.length > 0);
}

// Fetches TTS audio from /api/tts, returns a blob object URL ready for <audio>
export async function fetchTTSAudio(text: string, voiceId: string): Promise<string> {
  const res = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, voiceId }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error || `TTS request failed (${res.status})`);
  }
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

// Sends a recorded audio blob to /api/stt, returns the transcript string
export async function fetchSTTTranscript(audioBlob: Blob): Promise<string> {
  const form = new FormData();
  form.append("audio", audioBlob, "recording.webm");
  const res = await fetch("/api/stt", { method: "POST", body: form });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `STT request failed (${res.status})`);
  return data.transcript ?? "";
}
