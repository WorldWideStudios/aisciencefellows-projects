import { ChatRequest } from "./types";

export async function callLLM({
  system,
  messages,
  maxTokens = 1000,
  disableThinking = false,
}: ChatRequest): Promise<string> {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ system, messages, maxTokens, disableThinking }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || "Server error");
  return data.text;
}
