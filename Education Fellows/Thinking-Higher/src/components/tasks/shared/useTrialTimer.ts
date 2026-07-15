"use client";

import { useRef, useCallback } from "react";

interface TrialTimestamps {
  rt: number;
  startedAt: number;
  respondedAt: number;
  stimulusOnsetAt: number;
}

export function useTrialTimer() {
  const stimulusOnsetAt = useRef<number>(0);
  const trialStartedAt = useRef<number>(0);

  const markStimulusOnset = useCallback(() => {
    trialStartedAt.current = performance.now();
    requestAnimationFrame((rafTimestamp: number) => {
      stimulusOnsetAt.current = rafTimestamp;
    });
  }, []);

  const markResponse = useCallback((): TrialTimestamps => {
    const respondedAt = performance.now();
    const startedAt = trialStartedAt.current;
    const onset = stimulusOnsetAt.current;
    const rt = respondedAt - (onset > 0 ? onset : startedAt);

    return {
      rt,
      startedAt,
      respondedAt,
      stimulusOnsetAt: onset,
    };
  }, []);

  const reset = useCallback(() => {
    stimulusOnsetAt.current = 0;
    trialStartedAt.current = 0;
  }, []);

  return { markStimulusOnset, markResponse, reset };
}
