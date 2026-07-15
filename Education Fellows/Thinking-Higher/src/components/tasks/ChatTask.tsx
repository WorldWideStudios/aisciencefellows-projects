"use client";

import Simulation from "@/components/Simulation";
import type { ChatTrialData, TaskSummary } from "@/lib/types";

interface ChatTaskProps {
  onComplete: (trials: ChatTrialData[], summary: TaskSummary) => void;
}

export default function ChatTask({ onComplete }: ChatTaskProps) {
  return <Simulation onComplete={onComplete} />;
}
