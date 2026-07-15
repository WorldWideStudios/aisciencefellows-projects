"use client";

interface TaskInstructionsProps {
  title: string;
  instructions: string;
  onStart: () => void;
}

export default function TaskInstructions({
  title,
  instructions,
  onStart,
}: TaskInstructionsProps) {
  return (
    <div className="task-container">
      <div className="task-card" style={{ maxWidth: 600 }}>
        <div className="task-tag">COGNITIVE TASK</div>
        <h1 className="task-title">{title}</h1>
        <p className="task-text">{instructions}</p>
        <button className="start-btn" onClick={onStart}>
          Begin Task
        </button>
      </div>
    </div>
  );
}
