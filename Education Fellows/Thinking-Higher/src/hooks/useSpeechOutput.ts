"use client";
import { useRef, useState, useCallback } from "react";
import { chunkBySentence, fetchTTSAudio } from "@/lib/speech";

export interface UseSpeechOutputReturn {
  speak: (text: string, voiceId?: string) => void;
  stop: () => void;
  isSpeaking: boolean;
  currentChunk: string;   // sentence currently being spoken (for caption overlay)
}

export function useSpeechOutput(defaultVoice: string): UseSpeechOutputReturn {
  const [isSpeaking, setIsSpeaking]   = useState(false);
  const [currentChunk, setCurrentChunk] = useState("");
  const audioRef    = useRef<HTMLAudioElement | null>(null);
  const abortRef    = useRef(false);
  const objectUrls  = useRef<string[]>([]);
  // Keep default voice in a ref so speak() always reads the latest value
  const defaultVoiceRef = useRef(defaultVoice);
  defaultVoiceRef.current = defaultVoice;

  const revoke = () => {
    objectUrls.current.forEach((u) => URL.revokeObjectURL(u));
    objectUrls.current = [];
  };

  const stop = useCallback(() => {
    abortRef.current = true;
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.src = "";
    }
    revoke();
    setIsSpeaking(false);
    setCurrentChunk("");
  }, []);

  const speak = useCallback(async (text: string, voiceId?: string) => {
    stop();
    abortRef.current = false;

    // voiceId param takes priority; fall back to whatever defaultVoice is now
    const voice = voiceId ?? defaultVoiceRef.current;
    const chunks = chunkBySentence(text);
    if (chunks.length === 0) return;

    setIsSpeaking(true);

    if (!audioRef.current) audioRef.current = new Audio();
    const audio = audioRef.current;

    for (const chunk of chunks) {
      if (abortRef.current) break;
      try {
        setCurrentChunk(chunk);
        try {
          // Primary path: Amazon Polly via /api/tts
          const url = await fetchTTSAudio(chunk, voice);
          if (abortRef.current) { URL.revokeObjectURL(url); break; }
          objectUrls.current.push(url);
          audio.src = url;
          await new Promise<void>((resolve, reject) => {
            audio.onended  = () => resolve();
            audio.onerror  = () => reject(new Error("Audio playback error"));
            audio.play().catch(reject);
          });
          URL.revokeObjectURL(url);
          objectUrls.current = objectUrls.current.filter((u) => u !== url);
        } catch (apiError) {
          // Fallback: browser Web Speech API (no network, no AWS creds needed)
          console.warn("TTS API failed, falling back to Web Speech API:", apiError);
          await new Promise<void>((resolve, reject) => {
            if (abortRef.current || typeof window === "undefined" || !("speechSynthesis" in window)) {
              resolve();
              return;
            }
            const utterance = new SpeechSynthesisUtterance(chunk);
            utterance.onend   = () => resolve();
            utterance.onerror = () => reject(new Error("Web Speech fallback error"));
            window.speechSynthesis.speak(utterance);
          });
        }
      } catch (e) {
        console.error("TTS playback error:", e);
        break;
      }
    }

    if (!abortRef.current) {
      setIsSpeaking(false);
      setCurrentChunk("");
    }
  }, [stop]);

  return { speak, stop, isSpeaking, currentChunk };
}
