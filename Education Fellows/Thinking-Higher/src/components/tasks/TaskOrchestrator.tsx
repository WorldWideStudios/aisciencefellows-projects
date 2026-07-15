"use client";

import { useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import type {
  TaskSummary,
  BanditTrialData,
  ARCTrialData,
  ReversalTrialData,
  TwoStepTrialData,
  HanabiTrialData,
  ChatTrialData,
} from "@/lib/types";
import TaskInstructions from "./TaskInstructions";
import TaskDebrief from "./TaskDebrief";

interface CognitiveTaskConfig {
  taskId: string;
  taskType: string;
  title: string;
  description: string;
  numTrials: number;
  parameters: Record<string, number>;
  modelType: string;
  instructions: string;
  debrief: string;
}

interface RWFit {
  alpha: number;
  tau: number;
  logLikelihood: number;
  qValuesOverTime: [number, number][];
}

function LoadingState({ message }: { message: string }) {
  return (
    <div className="task-container">
      <div className="task-card" style={{ maxWidth: 400, textAlign: "center" }}>
        <div className="task-tag">LOADING</div>
        <p className="task-text">{message}</p>
      </div>
    </div>
  );
}

const TwoArmedBandit = dynamic(
  () => import("@/components/tasks/TwoArmedBandit"),
  { loading: () => <LoadingState message="Loading bandit task..." /> }
);

const ARCTask = dynamic(() => import("@/components/tasks/ARCTask"), {
  loading: () => <LoadingState message="Loading puzzle task..." />,
});

const ReversalLearning = dynamic(
  () => import("@/components/tasks/ReversalLearning"),
  { loading: () => <LoadingState message="Loading reversal task..." /> }
);

const TwoStepTask = dynamic(
  () => import("@/components/tasks/TwoStepTask"),
  { loading: () => <LoadingState message="Loading two-step task..." /> }
);

const HanabiGame = dynamic(
  () => import("@/components/tasks/HanabiGame"),
  { loading: () => <LoadingState message="Loading Hanabi..." /> }
);

const ChatTask = dynamic(
  () => import("@/components/tasks/ChatTask"),
  { loading: () => <LoadingState message="Loading simulation..." /> }
);

interface TaskOrchestratorProps {
  config: CognitiveTaskConfig;
}

type Phase = "instructions" | "task" | "debrief";

export default function TaskOrchestrator({ config }: TaskOrchestratorProps) {
  const [phase, setPhase] = useState<Phase>(config.taskType === "chat-simulation" ? "task" : "instructions");
  const [summary, setSummary] = useState<TaskSummary | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [trials, setTrials] = useState<any[]>([]);
  const [rwFit, setRwFit] = useState<RWFit | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [comparisonResult, setComparisonResult] = useState<any>(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const taskStartRef = useRef<number>(0);

  const handleStart = useCallback(() => {
    taskStartRef.current = Date.now();
    setPhase("task");
  }, []);

  const persistResult = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (taskTrials: any[], taskSummary: TaskSummary) => {
      fetch("/api/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          action: "saveTaskResult",
          result: {
            sessionId: "anonymous",
            stageId: config.taskId,
            taskType: config.taskType,
            trials: taskTrials,
            startedAt: taskStartRef.current,
            completedAt: Date.now(),
            summary: taskSummary,
          },
        }),
      }).catch(() => {});
    },
    [config.taskId, config.taskType]
  );

  const fetchComparison = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (taskType: string, taskTrials: any[]) => {
      setComparisonLoading(true);
      fetch("/api/compare", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          taskType,
          trials: taskTrials,
          options: { offline: true },
        }),
      })
        .then((r) => r.json())
        .then((data) => setComparisonResult(data.comparison))
        .catch(() => {})
        .finally(() => setComparisonLoading(false));
    },
    []
  );

  const handleBanditComplete = useCallback(
    async (banditTrials: BanditTrialData[], taskSummary: TaskSummary) => {
      setTrials(banditTrials);
      setSummary(taskSummary);
      persistResult(banditTrials, taskSummary);

      if (banditTrials.length > 0) {
        try {
          const { fitRW } = await import("@/lib/models/rescorla-wagner");
          const fit = fitRW(banditTrials);
          setRwFit(fit);
        } catch (err) {
          console.error("RW fitting failed:", err);
        }
      }

      // Fire Centaur comparison (non-blocking)
      fetchComparison(config.taskType, banditTrials);

      setPhase("debrief");
    },
    [persistResult, fetchComparison, config.taskType]
  );

  const handleARCComplete = useCallback(
    (arcTrials: ARCTrialData[], taskSummary: TaskSummary) => {
      setTrials(arcTrials);
      setSummary(taskSummary);
      persistResult(arcTrials, taskSummary);
      setPhase("debrief");
    },
    [persistResult]
  );

  const handleReversalComplete = useCallback(
    (reversalTrials: ReversalTrialData[], taskSummary: TaskSummary) => {
      setTrials(reversalTrials);
      setSummary(taskSummary);
      persistResult(reversalTrials, taskSummary);
      setPhase("debrief");
    },
    [persistResult]
  );

  const handleTwoStepComplete = useCallback(
    (twoStepTrials: TwoStepTrialData[], taskSummary: TaskSummary) => {
      setTrials(twoStepTrials);
      setSummary(taskSummary);
      persistResult(twoStepTrials, taskSummary);

      // Fire Centaur comparison (non-blocking)
      fetchComparison(config.taskType, twoStepTrials);

      setPhase("debrief");
    },
    [persistResult, fetchComparison, config.taskType]
  );

  const handleHanabiComplete = useCallback(
    (hanabiTrials: HanabiTrialData[], taskSummary: TaskSummary) => {
      setTrials(hanabiTrials);
      setSummary(taskSummary);
      persistResult(hanabiTrials, taskSummary);
      setPhase("debrief");
    },
    [persistResult]
  );

  const handleChatComplete = useCallback(
    (chatTrials: ChatTrialData[], taskSummary: TaskSummary) => {
      setTrials(chatTrials);
      setSummary(taskSummary);
      persistResult(chatTrials, taskSummary);
      setPhase("debrief");
    },
    [persistResult]
  );

  const handleContinue = useCallback(() => {
    window.location.href = "/tasks";
  }, []);

  if (phase === "instructions") {
    return (
      <TaskInstructions
        title={config.title}
        instructions={config.instructions}
        onStart={handleStart}
      />
    );
  }

  if (phase === "task") {
    switch (config.taskType) {
      case "two-armed-bandit":
        return (
          <TwoArmedBandit
            numTrials={config.numTrials}
            rewardProbabilities={[
              config.parameters.rewardProb1 ?? 0.7,
              config.parameters.rewardProb2 ?? 0.3,
            ]}
            onComplete={handleBanditComplete}
          />
        );
      case "arc-grid":
        return <ARCTaskWrapper onComplete={handleARCComplete} />;
      case "reversal-learning":
        return (
          <ReversalLearning
            numTrials={config.numTrials}
            reversalTrial={config.parameters.reversalTrial ?? 60}
            onComplete={handleReversalComplete}
          />
        );
      case "two-step":
        return (
          <TwoStepTask
            numTrials={config.numTrials}
            onComplete={handleTwoStepComplete}
          />
        );
      case "hanabi":
        return <HanabiGame onComplete={handleHanabiComplete} />;
      case "chat-simulation":
        return <ChatTask onComplete={handleChatComplete} />;
      default:
        return (
          <div className="task-container">
            <div className="task-card" style={{ maxWidth: 400, textAlign: "center" }}>
              <div className="task-tag">ERROR</div>
              <h1 className="task-title">Unknown Task Type</h1>
              <p className="task-text">
                Task type &quot;{config.taskType}&quot; is not recognized.
              </p>
              <button
                className="start-btn"
                onClick={() => (window.location.href = "/tasks")}
              >
                Back to Tasks
              </button>
            </div>
          </div>
        );
    }
  }

  if (!summary) return null;

  return (
    <TaskDebrief
      title={config.title}
      debriefText={config.debrief}
      summary={summary}
      taskType={config.taskType}
      rwFit={rwFit ?? undefined}
      trials={trials}
      comparisonResult={comparisonResult}
      comparisonLoading={comparisonLoading}
      onContinue={handleContinue}
    />
  );
}

function ARCTaskWrapper({
  onComplete,
}: {
  onComplete: (trials: ARCTrialData[], summary: TaskSummary) => void;
}) {
  const [puzzles, setPuzzles] = useState<null | any[]>(null);

  if (!puzzles) {
    import("@/data/tasks/arc-puzzles.json").then((mod) => {
      setPuzzles(mod.default.puzzles);
    });
    return <LoadingState message="Loading puzzles..." />;
  }

  return <ARCTask puzzles={puzzles} onComplete={onComplete} />;
}
