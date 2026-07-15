import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.resetModules();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  vi.stubEnv("GEMINI_API_KEY", "test-key");
  vi.stubEnv("GEMINI_MODEL", "gemini-1.5-flash");
});

function makeReqWithAudio(bytes: Uint8Array | null): NextRequest {
  const form = new FormData();
  if (bytes !== null) {
    form.append("audio", new File([bytes as BlobPart], "rec.webm", { type: "audio/webm" }));
  }
  return new NextRequest("http://localhost/api/stt", {
    method: "POST",
    body: form,
  });
}

function geminiResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function transcriptResult(text: string): unknown {
  return { candidates: [{ content: { parts: [{ text }] } }] };
}

describe("POST /api/stt", () => {
  it("returns 500 when GEMINI_API_KEY is missing", async () => {
    vi.stubEnv("GEMINI_API_KEY", "");
    const { POST } = await import("./route");
    const res = await POST(makeReqWithAudio(new Uint8Array([1, 2, 3])));
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/GEMINI_API_KEY/);
  });

  it("returns 400 when no audio file is uploaded", async () => {
    const { POST } = await import("./route");
    const res = await POST(makeReqWithAudio(null));
    expect(res.status).toBe(400);
    const body = await res.json();
    expect(body.error).toMatch(/audio file is required/i);
  });

  it("returns the transcript from the Gemini response", async () => {
    fetchMock.mockResolvedValueOnce(geminiResponse(transcriptResult("hello world")));
    const { POST } = await import("./route");
    const res = await POST(makeReqWithAudio(new Uint8Array([1, 2, 3])));
    expect(res.status).toBe(200);
    expect((await res.json()).transcript).toBe("hello world");
  });

  it("trims whitespace from the transcript", async () => {
    fetchMock.mockResolvedValueOnce(geminiResponse(transcriptResult("  spaced out  ")));
    const { POST } = await import("./route");
    const res = await POST(makeReqWithAudio(new Uint8Array([1, 2, 3])));
    expect((await res.json()).transcript).toBe("spaced out");
  });

  it("returns an empty transcript when Gemini returns no candidates", async () => {
    fetchMock.mockResolvedValueOnce(geminiResponse({}));
    const { POST } = await import("./route");
    const res = await POST(makeReqWithAudio(new Uint8Array([1, 2, 3])));
    expect(res.status).toBe(200);
    expect((await res.json()).transcript).toBe("");
  });

  it("propagates the Gemini error message and status", async () => {
    fetchMock.mockResolvedValueOnce(
      geminiResponse({ error: { message: "Unsupported audio mime type" } }, 400)
    );
    const { POST } = await import("./route");
    const res = await POST(makeReqWithAudio(new Uint8Array([1, 2, 3])));
    expect(res.status).toBe(400);
    expect((await res.json()).error).toBe("Unsupported audio mime type");
  });

  it("calls Gemini generateContent with the configured model and inline base64 audio", async () => {
    fetchMock.mockResolvedValueOnce(geminiResponse(transcriptResult("")));
    const { POST } = await import("./route");
    await POST(makeReqWithAudio(new Uint8Array([1, 2, 3])));

    expect(fetchMock).toHaveBeenCalledOnce();
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent");
    expect(url).toContain("key=test-key");
    const sentBody = JSON.parse(init.body);
    const parts = sentBody.contents[0].parts;
    expect(typeof parts[0].text).toBe("string");
    expect(parts[1].inlineData.mimeType).toBe("audio/webm");
    expect(parts[1].inlineData.data).toBe(Buffer.from([1, 2, 3]).toString("base64"));
    expect(sentBody.generationConfig.temperature).toBe(0.1);
  });
});
