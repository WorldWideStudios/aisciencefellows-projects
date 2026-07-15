"use client";

import { useCallback } from "react";
import ChatTask from "@/components/tasks/ChatTask";
import type { ChatTrialData, TaskSummary } from "@/lib/types";

export default function ChatTaskPage() {
  const handleComplete = useCallback(
    (_trials: ChatTrialData[], _summary: TaskSummary) => {
      // The simulation shows its own feedback overlay, so we don't
      // navigate away immediately. The user can close the overlay
      // and review stages, or navigate manually.
    },
    []
  );

  return <ChatTask onComplete={handleComplete} />;
}
