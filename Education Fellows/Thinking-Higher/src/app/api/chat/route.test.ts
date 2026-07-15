import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { NextRequest } from "next/server";

const fetchMock = vi.fn();

beforeEach(() => {
  vi.resetModules();
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
  vi.stubEnv("GEMINI_API_KEY", "test-key");
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

function makeReq(body: unknown): NextRequest {
  return new NextRequest("http://localhost/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

function geminiResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const validReply = {
  candidates: [
    { content: { parts: [{ text: "hello back" }] } },
  ],
};

describe("POST /api/chat — regression: 503 retry with backoff", () => {
  it("retries on 503 and succeeds when next attempt returns 200", async () => {
    fetchMock
      .mockResolvedValueOnce(geminiResponse({}, 503))
      .mockResolvedValueOnce(geminiResponse(validReply, 200));

    const { POST } = await import("./route");
    const promise = POST(
      makeReq({ system: "be helpful", messages: [{ role: "user", content: "hi" }] })
    );

    // First fetch is awaited synchronously; the 1s setTimeout fires before second fetch.
    await vi.advanceTimersByTimeAsync(1000);

    const res = await promise;
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(body.text).toBe("hello back");
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("retries up to 3 times then surfaces the final 503 error", async () => {
    fetchMock
      .mockResolvedValueOnce(geminiResponse({ error: { message: "Overloaded" } }, 503))
      .mockResolvedValueOnce(geminiResponse({ error: { message: "Overloaded" } }, 503))
      .mockResolvedValueOnce(geminiResponse({ error: { message: "Overloaded" } }, 503));

    const { POST } = await import("./route");
    const promise = POST(
      makeReq({ system: "x", messages: [{ role: "user", content: "hi" }] })
    );

    // Two backoff sleeps: 1s and 2s.
    await vi.advanceTimersByTimeAsync(1000);
    await vi.advanceTimersByTimeAsync(2000);

    const res = await promise;
    expect(res.status).toBe(503);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    const body = await res.json();
    expect(body.error).toBe("Overloaded");
  });

  it("does not retry on non-503 errors (e.g. 400 bad request)", async () => {
    fetchMock.mockResolvedValueOnce(
      geminiResponse({ error: { message: "Bad request" } }, 400)
    );

    const { POST } = await import("./route");
    const res = await POST(
      makeReq({ system: "x", messages: [{ role: "user", content: "hi" }] })
    );

    expect(res.status).toBe(400);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("succeeds without retry when first attempt returns 200", async () => {
    fetchMock.mockResolvedValueOnce(geminiResponse(validReply, 200));

    const { POST } = await import("./route");
    const res = await POST(
      makeReq({ system: "x", messages: [{ role: "user", content: "hi" }] })
    );

    expect(res.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});
