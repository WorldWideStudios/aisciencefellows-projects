import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

vi.mock("@/lib/speech", () => ({
  chunkBySentence: (t: string) =>
    t
      .split(/(?<=[.!?])\s+/)
      .map((s) => s.trim())
      .filter(Boolean),
  fetchTTSAudio: vi.fn(),
}));

class FakeAudio {
  src = "";
  onended: (() => void) | null = null;
  onerror: ((e: unknown) => void) | null = null;
  pause = vi.fn();
  play = vi.fn(() => {
    queueMicrotask(() => this.onended?.());
    return Promise.resolve();
  });
}

beforeEach(async () => {
  vi.stubGlobal("Audio", FakeAudio);
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:fake-url");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
  const { fetchTTSAudio } = await import("@/lib/speech");
  vi.mocked(fetchTTSAudio).mockReset();
  vi.mocked(fetchTTSAudio).mockResolvedValue("blob:fake-url");
});

describe("useSpeechOutput — regression: voiceId param overrides default", () => {
  it("uses the explicit voiceId argument when speak() provides one", async () => {
    const { useSpeechOutput } = await import("./useSpeechOutput");
    const { fetchTTSAudio } = await import("@/lib/speech");

    const { result } = renderHook(() => useSpeechOutput("Joanna"));

    await act(async () => {
      await result.current.speak("Hello world.", "Matthew");
    });

    expect(fetchTTSAudio).toHaveBeenCalled();
    for (const call of vi.mocked(fetchTTSAudio).mock.calls) {
      expect(call[1]).toBe("Matthew");
    }
  });

  it("falls back to defaultVoice when no voiceId is provided", async () => {
    const { useSpeechOutput } = await import("./useSpeechOutput");
    const { fetchTTSAudio } = await import("@/lib/speech");

    const { result } = renderHook(() => useSpeechOutput("Ruth"));

    await act(async () => {
      await result.current.speak("Hello.");
    });

    expect(fetchTTSAudio).toHaveBeenCalledWith(expect.any(String), "Ruth");
  });

  it("uses the latest defaultVoice via ref even after re-renders", async () => {
    const { useSpeechOutput } = await import("./useSpeechOutput");
    const { fetchTTSAudio } = await import("@/lib/speech");

    const { result, rerender } = renderHook(
      ({ voice }: { voice: string }) => useSpeechOutput(voice),
      { initialProps: { voice: "Joanna" } }
    );

    rerender({ voice: "Brian" });

    await act(async () => {
      await result.current.speak("Hello.");
    });

    expect(fetchTTSAudio).toHaveBeenCalledWith(expect.any(String), "Brian");
  });
});
