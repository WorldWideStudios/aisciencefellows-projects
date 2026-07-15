import { notFound } from "next/navigation";
import TaskOrchestrator from "@/components/tasks/TaskOrchestrator";
import banditConfig from "@/data/tasks/bandit-2arm.json";
import arcConfig from "@/data/tasks/arc-grid.json";
import reversalConfig from "@/data/tasks/reversal-learning.json";
import twoStepConfig from "@/data/tasks/two-step.json";
import hanabiConfig from "@/data/tasks/hanabi.json";
import chatConfig from "@/data/tasks/chat-simulation.json";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const TASK_CONFIGS: Record<string, any> = {
  "bandit-2arm": banditConfig,
  "arc-grid": arcConfig,
  "reversal-learning": reversalConfig,
  "two-step": twoStepConfig,
  "hanabi": hanabiConfig,
  "chat-simulation": chatConfig,
};

interface TaskPageProps {
  params: Promise<{ taskId: string }>;
}

export default async function TaskPage({ params }: TaskPageProps) {
  const { taskId } = await params;

  const config = TASK_CONFIGS[taskId];

  if (!config) {
    notFound();
  }

  return <TaskOrchestrator config={config} />;
}
