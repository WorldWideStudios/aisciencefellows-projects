import { describe, it, expect, vi, beforeEach } from "vitest";
import { NextRequest } from "next/server";

const sendMock = vi.fn();

vi.mock("@aws-sdk/client-polly", () => {
  class PollyClient {
    send = sendMock;
  }
  const SynthesizeSpeechCommand = vi.fn(function (this: object, input: unknown) {
    Object.assign(this, { input });
  });
  return {
    PollyClient,
    SynthesizeSpeechCommand,
    Engine: { NEURAL: "neural" },
    OutputFormat: { MP3: "mp3" },
    TextType: { TEXT: "text" },
  };
});

function makeReq(body: unknown): NextRequest {
  return new NextRequest("http://localhost/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function audioStream(bytes: Uint8Array[]) {
  return {
    [Symbol.asyncIterator]: async function* () {
      for (const b of bytes) yield b;
    },
  };
}

beforeEach(async () => {
  vi.resetModules();
  sendMock.mockReset();
  const { SynthesizeSpeechCommand } = await import("@aws-sdk/client-polly");
  vi.mocked(SynthesizeSpeechCommand).mockClear();
  vi.stubEnv("AWS_ACCESS_KEY_ID", "test-key");
  vi.stubEnv("AWS_SECRET_ACCESS_KEY", "test-secret");
  vi.stubEnv("AWS_REGION", "us-east-1");
});

describe("POST /api/tts", () => {
  it("returns 500 when AWS credentials are missing", async () => {
    vi.stubEnv("AWS_ACCESS_KEY_ID", "");
    vi.stubEnv("AWS_SECRET_ACCESS_KEY", "");
    const { POST } = await import("./route");
    const res = await POST(makeReq({ text: "hi" }));
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toMatch(/AWS credentials/i);
  });

  it("returns 400 when text is missing", async () => {
    const { POST } = await import("./route");
    const res = await POST(makeReq({}));
    expect(res.status).toBe(400);
  });

  it("returns 400 when text is not a string", async () => {
    const { POST } = await import("./route");
    const res = await POST(makeReq({ text: 123 }));
    expect(res.status).toBe(400);
  });

  it("falls back to Joanna when voiceId is not in the allowlist", async () => {
    sendMock.mockResolvedValueOnce({
      AudioStream: audioStream([new Uint8Array([1, 2, 3])]),
    });
    const { POST } = await import("./route");
    await POST(makeReq({ text: "hi", voiceId: "Bogus" }));
    const { SynthesizeSpeechCommand } = await import("@aws-sdk/client-polly");
    expect(SynthesizeSpeechCommand).toHaveBeenLastCalledWith(
      expect.objectContaining({ VoiceId: "Joanna" })
    );
  });

  it("passes through valid voiceId", async () => {
    sendMock.mockResolvedValueOnce({
      AudioStream: audioStream([new Uint8Array([1])]),
    });
    const { POST } = await import("./route");
    await POST(makeReq({ text: "hi", voiceId: "Matthew" }));
    const { SynthesizeSpeechCommand } = await import("@aws-sdk/client-polly");
    expect(SynthesizeSpeechCommand).toHaveBeenLastCalledWith(
      expect.objectContaining({ VoiceId: "Matthew" })
    );
  });

  it("truncates text longer than 3000 characters", async () => {
    sendMock.mockResolvedValueOnce({
      AudioStream: audioStream([new Uint8Array([1])]),
    });
    const longText = "x".repeat(5000);
    const { POST } = await import("./route");
    await POST(makeReq({ text: longText }));
    const { SynthesizeSpeechCommand } = await import("@aws-sdk/client-polly");
    expect(SynthesizeSpeechCommand).toHaveBeenLastCalledWith(
      expect.objectContaining({ Text: "x".repeat(3000) })
    );
  });

  it("returns audio/mpeg with synthesized bytes on success", async () => {
    const bytes = new Uint8Array([0xff, 0xfb, 0x90, 0x44]);
    sendMock.mockResolvedValueOnce({ AudioStream: audioStream([bytes]) });
    const { POST } = await import("./route");
    const res = await POST(makeReq({ text: "hi" }));
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toBe("audio/mpeg");
    expect(res.headers.get("Cache-Control")).toBe("no-store");
    const buf = new Uint8Array(await res.arrayBuffer());
    expect(buf).toEqual(bytes);
  });

  it("returns 502 when Polly returns no AudioStream", async () => {
    sendMock.mockResolvedValueOnce({});
    const { POST } = await import("./route");
    const res = await POST(makeReq({ text: "hi" }));
    expect(res.status).toBe(502);
  });

  it("returns 500 when Polly throws", async () => {
    sendMock.mockRejectedValueOnce(new Error("Polly is down"));
    const { POST } = await import("./route");
    const res = await POST(makeReq({ text: "hi" }));
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body.error).toBe("Polly is down");
  });
});
