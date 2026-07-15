"use client";
import { useRef, useState, useCallback } from "react";
import { fetchSTTTranscript } from "@/lib/speech";

// Only two visible states — "processing" is silent/internal
export type SpeechInputState = "idle" | "listening";

export interface UseSpeechInputReturn {
  state: SpeechInputState;
  interimText: string;           // "Listening…" shown while recording
  supported: boolean;
  start: () => Promise<void>;
  stop: () => void;
  onTranscript: (cb: (text: string) => void) => void;
}

export function useSpeechInput(): UseSpeechInputReturn {
  const [state, setState]             = useState<SpeechInputState>("idle");
  const [interimText, setInterimText] = useState("");
  const processingRef    = useRef(false);   // internal guard — prevents double-start
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef        = useRef<Blob[]>([]);
  const callbackRef      = useRef<((text: string) => void) | null>(null);

  const supported = typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia;

  const onTranscript = useCallback((cb: (text: string) => void) => {
    callbackRef.current = cb;
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const start = useCallback(async () => {
    if (state !== "idle" || processingRef.current) return;
    chunksRef.current = [];
    setInterimText("Listening…");

    let stream: MediaStream;
    try {
      // Use constraints to heavily prefer a local communications microphone over Continuity Camera
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        }
      });
    } catch {
      setInterimText("Microphone access denied");
      setTimeout(() => setInterimText(""), 3000);
      return;
    }

    // Explicitly try to record in webm if supported (Chrome/Firefox/New Safari), else default (Safari)
    const options = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? { mimeType: "audio/webm;codecs=opus" } :
                    MediaRecorder.isTypeSupported("audio/webm") ? { mimeType: "audio/webm" } : {};
    
    const mr = new MediaRecorder(stream, options);
    mediaRecorderRef.current = mr;
    mr.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };

    mr.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());

      // Return to idle immediately — STT happens silently in background
      setState("idle");
      setInterimText("Transcribing...");
      processingRef.current = true;
      try {
        const mimeType = mr.mimeType || "audio/webm";
        const blob       = new Blob(chunksRef.current, { type: mimeType });
        const transcript = await fetchSTTTranscript(blob);
        
        if (transcript && callbackRef.current) {
          callbackRef.current(transcript);
          setInterimText("");
        } else if (!transcript) {
           setInterimText("Could not hear anything.");
           setTimeout(() => setInterimText(""), 3000);
        }
      } catch (e) {
        console.error("STT error:", e);
        setInterimText("Error: could not transcribe");
        setTimeout(() => setInterimText(""), 3000);
      } finally {
        processingRef.current = false;
      }
    };

    mr.start();
    setState("listening");
  }, [state]);

  return { state, interimText, supported, start, stop: stopRecording, onTranscript };
}
